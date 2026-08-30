"""
model_check.py
--------------
Standalone visual check: confirms vehicle_model and plate_model are detecting
correctly on real frames from your video, before trusting the full pipeline.
Run this, look at the saved crop images, then delete/ignore this file once confirmed.
"""

import os
import cv2
from ultralytics import YOLO

# ============================================================
# CONFIG — match your actual filenames/paths
# ============================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

VEHICLE_MODEL_PATH = os.path.join(SCRIPT_DIR, "vehiclemodelv8m.pt")
PLATE_MODEL_PATH = os.path.join(SCRIPT_DIR, "plate_model.pt")
VIDEO_PATH = os.path.join(SCRIPT_DIR, "/Users/bahrudeen/Documents/5th sem /SIH/test video anpr3.mp4")  # <-- set your actual video path

OUTPUT_DIR = os.path.join(SCRIPT_DIR, "model_check_output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

VEHICLE_CLASSES = {2: 'car', 3: 'motorcycle', 5: 'bus', 7: 'truck'}
CHECK_EVERY_N_FRAMES = 15   # how often to sample a frame for checking
PAD = 0                    # same padding your main pipeline uses


# ============================================================
# LOAD MODELS
# ============================================================
print(f"Loading vehicle model: {VEHICLE_MODEL_PATH}")
vehicle_model = YOLO(VEHICLE_MODEL_PATH)

print(f"Loading plate model: {PLATE_MODEL_PATH}")
plate_model = YOLO(PLATE_MODEL_PATH)


# ============================================================
# RUN CHECK
# ============================================================
cap = cv2.VideoCapture(VIDEO_PATH)
if not cap.isOpened():
    raise IOError(f"Could not open video: {VIDEO_PATH}")

frame_count = 0
saved_count = 0

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break
    frame_count += 1

    if frame_count % CHECK_EVERY_N_FRAMES != 0:
        continue

    print(f"\n{'='*50}\nFRAME {frame_count}\n{'='*50}")

    # ---- Vehicle detection ----
    vresults = vehicle_model(frame, verbose=False)[0]
    vehicles = [b for b in vresults.boxes if int(b.cls[0]) in VEHICLE_CLASSES]

    if not vehicles:
        print("  No vehicle detected in this frame.")
        continue

    for i, vbox in enumerate(vehicles):
        cls_id = int(vbox.cls[0])
        v_conf = float(vbox.conf[0])
        x1, y1, x2, y2 = [int(v) for v in vbox.xyxy[0].tolist()]
        vehicle_crop = frame[y1:y2, x1:x2]

        if vehicle_crop.size == 0:
            continue

        print(f"  Vehicle {i+1}: class={VEHICLE_CLASSES[cls_id]}  conf={v_conf:.2f}  bbox=({x1},{y1},{x2},{y2})")

        # Save the full frame with the vehicle box drawn, for visual confirmation
        annotated = frame.copy()
        cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(annotated, f"{VEHICLE_CLASSES[cls_id]} {v_conf:.2f}", (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        vehicle_crop_path = os.path.join(OUTPUT_DIR, f"frame{frame_count}_vehicle{i+1}_crop.jpg")
        cv2.imwrite(vehicle_crop_path, vehicle_crop)
        annotated_path = os.path.join(OUTPUT_DIR, f"frame{frame_count}_vehicle{i+1}_annotated.jpg")
        cv2.imwrite(annotated_path, annotated)

        # ---- Plate detection on this vehicle crop ----
        presults = plate_model(vehicle_crop, verbose=False)[0]

        if len(presults.boxes) == 0:
            print(f"    No plate detected in vehicle {i+1}'s crop.")
            continue

        plate_box = max(presults.boxes, key=lambda b: float(b.conf[0]))
        p_conf = float(plate_box.conf[0])
        px1, py1, px2, py2 = [int(v) for v in plate_box.xyxy[0].tolist()]

        h_v, w_v = vehicle_crop.shape[:2]
        px1 = max(0, px1 - PAD)
        py1 = max(0, py1 - PAD)
        px2 = min(w_v, px2 + PAD)
        py2 = min(h_v, py2 + PAD)
        plate_crop = vehicle_crop[py1:py2, px1:px2]

        if plate_crop.size == 0:
            print(f"    Plate crop empty after padding for vehicle {i+1}.")
            continue

        print(f"    Plate detected: conf={p_conf:.2f}  bbox=({px1},{py1},{px2},{py2})")

        plate_crop_path = os.path.join(OUTPUT_DIR, f"frame{frame_count}_vehicle{i+1}_plate.jpg")
        cv2.imwrite(plate_crop_path, plate_crop)
        saved_count += 1

cap.release()

print(f"\n--- Done. Saved {saved_count} plate crops + vehicle crops/annotated frames to: {OUTPUT_DIR} ---")
print("Open that folder in VS Code's file explorer and inspect the images directly.")