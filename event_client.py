import os
from datetime import datetime, timezone
from typing import List, Optional

import requests


BASE_URL = os.getenv("BACKEND_BASE_URL", "http://172.16.97.217:8000")
DEFAULT_CAMERA_ID = os.getenv("DEFAULT_CAMERA_ID", "CAM_AN_02")


def send_vehicle_event(
    camera_id: str,
    plate_text: str,
    ocr_confidence: float,
    timestamp: Optional[str] = None,
    vehicle_class: Optional[str] = None,
    vehicle_color: Optional[str] = None,
    embedding: Optional[List[float]] = None,
    plate_crop_url: Optional[str] = None,
    base_url: str = BASE_URL,
):
    """
    Send a vehicle detection/OCR event to the FastAPI backend.

    Payload matches the backend schema expected by:
        POST /api/v1/events
    """
    if not camera_id or not plate_text:
        raise ValueError("camera_id and plate_text are required.")

    if timestamp is None:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    payload = {
        "camera_id": camera_id,
        "plate_text": plate_text,
        "ocr_confidence": float(ocr_confidence),
        "timestamp": timestamp,
    }

    if vehicle_class is not None:
        payload["vehicle_class"] = vehicle_class
    if vehicle_color is not None:
        payload["vehicle_color"] = vehicle_color
    if embedding is not None:
        payload["embedding"] = list(embedding)
    if plate_crop_url is not None:
        payload["plate_crop_url"] = plate_crop_url

    url = f"{base_url.rstrip('/')}/api/v1/events"
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=3)

        if response.status_code == 201:
            print(f"[ML Event] Successfully sent vehicle event for camera_id={camera_id}")
            return response.json() if response.content else {"status": "created"}

        print(
            f"[ML Event] Failed to send event: HTTP {response.status_code} | "
            f"url={url} | body={response.text[:200]}"
        )
        return None

    except requests.RequestException as exc:
        print(f"[ML Event] Error sending event to {url}: {exc}")
        return None


if __name__ == "__main__":
    sample_embedding = [0.142, -0.052, 0.811]
    send_vehicle_event(
        camera_id=DEFAULT_CAMERA_ID,
        plate_text="KA05AB1234",
        ocr_confidence=0.97,
        vehicle_class="SUV",
        vehicle_color="White",
        embedding=sample_embedding,
        plate_crop_url="https://example.com/plate_crop.jpg",
        base_url=BASE_URL,
    )
