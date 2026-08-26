
import cv2
import json
import numpy as np
from datetime import datetime
from ultralytics import YOLO
from huggingface_hub import hf_hub_download
from paddleocr import PaddleOCR

#Load Models

#this model is the model used to detect vehicles
#i used nano previously, but have replaced a medium now
vehicle_model = YOLO('yolov8m.pt')

#License plate detector (pretrained, from Hugging Face)
plate_model_path = hf_hub_download(
    repo_id="keremberke/yolov8n-license-plate-detection",
    filename="best.pt"
)
plate_model = YOLO(plate_model_path)

#OCR model
ocr_model = PaddleOCR(use_angle_cls=True, lang='en')





#functions
def parse_ocr_result(result):
    """Works with PaddleOCR 3.x / PaddleX pipeline output (from .predict())"""
    parsed = []
    if not result:
        return parsed
    res = result[0]
    texts = res['rec_texts']
    scores = res['rec_scores']
    boxes = res['rec_boxes']

    for text, score, box in zip(texts, scores, boxes):
        parsed.append({
            'text': text,
            'confidence': float(score),
            'bbox': box
        })
    return parsed


def combine_plate_text(detections):
    """Combines multiple detected text regions into one plate string, left to right."""
    if not detections:
        return None, 0.0
    # rec_boxes format is [x1, y1, x2, y2] -> bbox[0] is x1 directly
    sorted_dets = sorted(detections, key=lambda d: d['bbox'][0])
    full_text = ''.join(d['text'] for d in sorted_dets)
    avg_conf = sum(d['confidence'] for d in sorted_dets) / len(sorted_dets)
    return full_text, avg_conf


def compute_final_confidence_v2(vehicle_conf, plate_conf, ocr_conf, min_threshold=0.5):
    """
    Rejects immediately if any single stage is below threshold —
    avoids hiding a weak stage behind a simple average.
    """
    if min(vehicle_conf, plate_conf, ocr_conf) < min_threshold:
        return 0.0, "REJECTED — low confidence stage detected"
    avg = (vehicle_conf + plate_conf + ocr_conf) / 3
    return round(avg, 4), "OK"


def bgr_to_color_name(b, g, r):
    """Rough mapping of BGR values to common vehicle color names."""
    colors = {
        'white':  (255, 255, 255),
        'black':  (0, 0, 0),
        'gray':   (128, 128, 128),
        'silver': (192, 192, 192),
        'red':    (0, 0, 255),
        'blue':   (255, 0, 0),
        'green':  (0, 128, 0),
        'yellow': (0, 255, 255),
    }
    min_dist = float('inf')
    closest = 'unknown'
    for name, (cb, cg, cr) in colors.items():
        dist = (b - cb)**2 + (g - cg)**2 + (r - cr)**2
        if dist < min_dist:
            min_dist = dist
            closest = name
    return closest


def get_dominant_color(image_crop, k=3):
    """Finds the dominant color in a vehicle crop using k-means clustering."""
    small = cv2.resize(image_crop, (50, 50))
    pixels = small.reshape(-1, 3).astype(np.float32)

    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
    _, labels, centers = cv2.kmeans(pixels, k, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)

    counts = np.bincount(labels.flatten())
    dominant_bgr = centers[np.argmax(counts)]
    b, g, r = dominant_bgr
    return bgr_to_color_name(b, g, r)




#PIPELINE

VEHICLE_CLASSES = {2: 'car', 3: 'motorcycle', 5: 'bus', 7: 'truck'}

def run_anpr_pipeline(image_path, camera_id="CAM01",
                        vehicle_model=vehicle_model, plate_model=plate_model, ocr_model=ocr_model):
    """
    Full ANPR pipeline: image -> vehicle detection -> plate detection -> OCR -> JSON event
    """
    img = cv2.imread(image_path)
    if img is None:
        return {"error": f"Could not read image: {image_path}"}

    # ---- Stage 1: Vehicle detection ----
    vresults = vehicle_model(img, verbose=False)[0]

    detected_vehicles = []
    for box in vresults.boxes:
        cls_id = int(box.cls[0])
        if cls_id in VEHICLE_CLASSES:
            detected_vehicles.append({
                'class': VEHICLE_CLASSES[cls_id],
                'confidence': float(box.conf[0]),
                'bbox': box.xyxy[0].tolist()
            })

    if not detected_vehicles:
        return {"error": "No vehicle detected"}

    vehicle = max(detected_vehicles, key=lambda v: v['confidence'])
    x1, y1, x2, y2 = [int(v) for v in vehicle['bbox']]
    vehicle_crop = img[y1:y2, x1:x2]

    vehicle_color = get_dominant_color(vehicle_crop)

    # ---- Stage 2: Plate detection ----
    presults = plate_model(vehicle_crop, verbose=False)[0]
    if len(presults.boxes) == 0:
        return {
            "error": "No plate detected",
            "vehicle_class": vehicle['class'],
            "vehicle_color": vehicle_color,
            "vehicle_confidence": vehicle['confidence']
        }

    plate_box = presults.boxes[0]
    plate_conf = float(plate_box.conf[0])
    px1, py1, px2, py2 = [int(v) for v in plate_box.xyxy[0].tolist()]
    plate_crop = vehicle_crop[py1:py2, px1:px2]

    if plate_crop.size == 0:
        return {"error": "Empty plate crop"}

    # ---- Stage 3: OCR ----
    temp_path = "_temp_plate_crop.jpg"
    cv2.imwrite(temp_path, plate_crop)
    ocr_result = ocr_model.predict(temp_path)

    detections = parse_ocr_result(ocr_result)
    plate_text, ocr_conf = combine_plate_text(detections)

    if plate_text is None:
        return {
            "error": "OCR found no text",
            "vehicle_class": vehicle['class'],
            "vehicle_color": vehicle_color,
            "vehicle_confidence": vehicle['confidence'],
            "plate_confidence": plate_conf
        }

    # ---- Stage 4: Confidence scoring ----
    final_conf, status = compute_final_confidence_v2(vehicle['confidence'], plate_conf, ocr_conf)

    # ---- Stage 5: Event generation ----
    event = {
        "plate": plate_text,
        "vehicle_class": vehicle['class'],
        "vehicle_color": vehicle_color,
        "confidence": final_conf,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "camera_id": camera_id,
        "_debug": {
            "vehicle_confidence": round(vehicle['confidence'], 4),
            "plate_confidence": round(plate_conf, 4),
            "ocr_confidence": round(ocr_conf, 4),
            "status": status
        }
    }
    return event

if __name__ == "__main__":
    event = run_anpr_pipeline("test.jpg", camera_id="CAM01")
    print(json.dumps(event, indent=2))
