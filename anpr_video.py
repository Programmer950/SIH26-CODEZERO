"""
ANPR Video Pipeline
--------------------
Video -> Vehicle Detection + Tracking -> Plate Detection -> NVIDIA Vision OCR
Collects ALL valid readings per vehicle across its full appearance in the video,
then finalizes the answer via majority vote once the vehicle's track ends
(or the video finishes) — not a running "best so far" printed mid-stream.
"""

import os
import cv2
import json
import base64
import re
import numpy as np
import requests
from datetime import datetime
from collections import defaultdict, Counter
from dotenv import load_dotenv
from ultralytics import YOLO

load_dotenv()

# ============================================================
# CONFIG
# ============================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

VEHICLE_MODEL_PATH = os.path.join(SCRIPT_DIR, "vehiclemodelv8m.pt")
PLATE_MODEL_PATH = os.path.join(SCRIPT_DIR, "plate_model.pt")
VIDEO_PATH = os.path.join(SCRIPT_DIR, "/Users/bahrudeen/Downloads/toTest.mp4")  # <-- set your actual video path
CAMERA_ID = "CAM01"

SAMPLE_EVERY_N = 2                  # how often (in frames) to attempt plate detection + OCR
PLATE_CROP_PADDING = 10             # pixels of padding around detected plate box
BLUR_THRESHOLD = 100.0              # below this = too blurry to bother OCR-ing (tune based on your footage)
MAX_READINGS_PER_TRACK = 8          # cap how many OCR calls we spend per vehicle — avoids wasting API calls
TRACK_TIMEOUT_FRAMES = 30           # if a track hasn't been seen for this many frames, consider it "gone" and finalize it

VEHICLE_CLASSES = {2: 'car', 3: 'motorcycle', 5: 'bus', 7: 'truck'}

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
if not NVIDIA_API_KEY:
    raise EnvironmentError("NVIDIA_API_KEY not set. Check your .env file.")

NVIDIA_VISION_URL = "https://integrate.api.nvidia.com/v1/chat/completions"


# ============================================================
# NVIDIA VISION OCR
# ============================================================
class NvidiaVisionPlateOCR:
    def __init__(self, api_key: str, model_name: str = "meta/llama-3.2-11b-vision-instruct"):
        self.api_key = api_key
        self.model_name = model_name
        self.headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        self.session = requests.Session()

    def recognize(self, image_crop: np.ndarray) -> tuple[str, float]:
        if image_crop is None or image_crop.size == 0:
            return "", 0.0
        success, buffer = cv2.imencode('.jpg', image_crop, [cv2.IMWRITE_JPEG_QUALITY, 92])
        if not success:
            return "", 0.0
        b64_image = base64.b64encode(buffer).decode('utf-8')

        payload = {
            "model": self.model_name,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": (
                        "Read the vehicle license plate number in this image. "
                        "Output ONLY the uppercase alphanumeric license plate number "
                        "(for example: HR26DQ5551). Discard country logos or prefixes like IND. "
                        "Do NOT include spaces, punctuation, or conversational words."
                    )},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"}}
                ]
            }],
            "max_tokens": 20,
            "temperature": 0.0
        }
        try:
            response = self.session.post(NVIDIA_VISION_URL, headers=self.headers, json=payload, timeout=25)
            if response.status_code == 200:
                content = response.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                clean_plate = self._extract_plate(content)
                if clean_plate:
                    return clean_plate, 0.9  # placeholder confidence — see earlier note
            else:
                print(f"[NVIDIA Vision AI] Status {response.status_code}: {response.text[:150]}")
        except Exception as e:
            print(f"[NVIDIA Vision AI] Request error: {e}")
        return "", 0.0

    @staticmethod
    def _extract_plate(raw_text: str) -> str:
        tokens = re.findall(r'[A-Za-z0-9]+', raw_text)
        merged = "".join(tokens).upper()
        if merged.startswith("IND") and len(merged) > 6:
            merged = merged[3:]
        if merged.endswith("IND") and len(merged) > 6:
            merged = merged[:-3]
        return merged


def preprocess_license_plate(crop: np.ndarray) -> np.ndarray:
    if crop is None or crop.size == 0:
        return crop
    target_h = 140
    h, w = crop.shape[:2]
    scale = max(target_h / float(h), 1.2)
    resized = cv2.resize(crop, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_LANCZOS4)
    lab = cv2.cvtColor(resized, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    cl = clahe.apply(l)
    enhanced = cv2.merge((cl, a, b))
    return cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)


def compute_blur_score(image: np.ndarray) -> float:
    """
    Variance of the Laplacian — a standard, cheap blur-detection metric.
    LOW variance = blurry/flat (little edge detail). HIGH variance = sharp.
    This lets us skip OCR entirely on crops too blurry to realistically read,
    saving API calls and avoiding noisy garbage readings polluting the vote.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return cv2.Laplacian(gray, cv2.CV_64F).var()


# ============================================================
# LOAD MODELS
# ============================================================
print(f"Loading vehicle model: {VEHICLE_MODEL_PATH}")
vehicle_model = YOLO(VEHICLE_MODEL_PATH)
print(f"Loading plate model: {PLATE_MODEL_PATH}")
plate_model = YOLO(PLATE_MODEL_PATH)
print("Initializing NVIDIA Vision AI OCR...")
ocr = NvidiaVisionPlateOCR(api_key=NVIDIA_API_KEY)


# ============================================================
# PER-TRACK STATE
# ============================================================
track_class_history = defaultdict(list)     # track_id -> list of class labels seen
track_readings = defaultdict(list)          # track_id -> list of (plate_text, confidence) — ALL valid reads
track_last_seen_frame = {}                  # track_id -> last frame number it appeared in
finalized_tracks = set()                    # track_ids we've already printed a final answer for


def finalize_track(tid):
    """
    Called once a track is considered 'done' (vehicle left frame, or video ended).
    Picks the FINAL answer using majority vote across ALL readings collected
    for this vehicle — not a single frame's confidence.
    """
    if tid in finalized_tracks:
        return
    finalized_tracks.add(tid)

    readings = track_readings.get(tid, [])
    stable_class = Counter(track_class_history[tid]).most_common(1)[0][0] if track_class_history[tid] else "unknown"

    if not readings:
        plate_text, confidence = "NOT READ", 0.0
    else:
        # Majority vote on exact text match — most repeated string wins.
        # This is a stronger signal than trusting a single high-confidence read,
        # since OCR can be confidently wrong on one frame but agree across several.
        text_counts = Counter(text for text, conf in readings)
        best_text, vote_count = text_counts.most_common(1)[0]
        # average confidence of the readings that match the winning text
        matching_confidences = [conf for text, conf in readings if text == best_text]
        confidence = round(sum(matching_confidences) / len(matching_confidences), 4)
        plate_text = best_text

        print(f"  (vehicle {tid}: {len(readings)} total reads, "
              f"winning text '{plate_text}' appeared {vote_count}x)")

    event = {
        "vehicle_id": tid,
        "vehicle_class": stable_class,
        "plate": plate_text,
        "confidence": confidence,
        "camera_id": CAMERA_ID,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    print(json.dumps(event, indent=2))
    return event


# ============================================================
# VIDEO PROCESSING
# ============================================================
cap = cv2.VideoCapture(VIDEO_PATH)
if not cap.isOpened():
    raise IOError(f"Could not open video: {VIDEO_PATH}")

frame_count = 0

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break
    frame_count += 1

    results = vehicle_model.track(frame, persist=True, verbose=False)[0]

    active_track_ids_this_frame = set()

    if results.boxes.id is not None:
        for box, track_id in zip(results.boxes, results.boxes.id):
            cls_id = int(box.cls[0])
            if cls_id not in VEHICLE_CLASSES:
                continue

            tid = int(track_id)
            active_track_ids_this_frame.add(tid)
            track_class_history[tid].append(VEHICLE_CLASSES[cls_id])
            track_last_seen_frame[tid] = frame_count

            if frame_count % SAMPLE_EVERY_N != 0:
                continue
            if len(track_readings[tid]) >= MAX_READINGS_PER_TRACK:
                continue  # already have enough samples for this vehicle, stop spending API calls

            x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
            vehicle_crop = frame[y1:y2, x1:x2]
            if vehicle_crop.size == 0:
                continue

            presults = plate_model(vehicle_crop, verbose=False)[0]
            if len(presults.boxes) == 0:
                continue

            plate_box = max(presults.boxes, key=lambda b: float(b.conf[0]))
            plate_conf = float(plate_box.conf[0])
            px1, py1, px2, py2 = [int(v) for v in plate_box.xyxy[0].tolist()]

            h_v, w_v = vehicle_crop.shape[:2]
            px1 = max(0, px1 - PLATE_CROP_PADDING)
            py1 = max(0, py1 - PLATE_CROP_PADDING)
            px2 = min(w_v, px2 + PLATE_CROP_PADDING)
            py2 = min(h_v, py2 + PLATE_CROP_PADDING)
            plate_crop = vehicle_crop[py1:py2, px1:px2]
            if plate_crop.size == 0:
                continue

            # --- Blur pre-filter: skip OCR entirely on unreadable crops ---
            blur_score = compute_blur_score(plate_crop)
            if blur_score < BLUR_THRESHOLD:
                continue  # too blurry, don't waste an OCR call on it

            enhanced_crop = preprocess_license_plate(plate_crop)
            plate_text, ocr_conf = ocr.recognize(enhanced_crop)

            if not plate_text or len(plate_text) < 4:
                continue

            overall_conf = round((plate_conf + ocr_conf) / 2, 4)
            track_readings[tid].append((plate_text, overall_conf))

    # --- Finalize any tracks that have disappeared (vehicle left frame) ---
    for tid, last_frame in list(track_last_seen_frame.items()):
        if tid not in active_track_ids_this_frame and (frame_count - last_frame) > TRACK_TIMEOUT_FRAMES:
            finalize_track(tid)

cap.release()

# --- Finalize anything still active when the video ended ---
for tid in track_last_seen_frame:
    finalize_track(tid)

print("\n--- Video processing complete ---")