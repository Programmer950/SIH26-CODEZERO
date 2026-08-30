# ANPR Video Pipeline

This project performs automatic number plate recognition (ANPR) on video footage by combining:

- vehicle detection and tracking
- license plate detection
- OCR via the NVIDIA Vision API
- majority-vote finalization per vehicle track
- sending real-time detection events to a FastAPI dashboard backend

## Project Structure

- `anpr_video.py` — main video processing pipeline
- `event_client.py` — utility for posting OCR/vehicle events to the backend API
- `model_check.py` — lightweight model sanity check / verification script
- `vehiclemodelv8m.pt` — vehicle detection model
- `plate_model.pt` — plate detection model
- `.env` — local environment variables (ignored by Git)

## Setup

1. Create a virtual environment (optional but recommended):
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Add your NVIDIA API key to the local environment file:
   ```bash
   cp .env .env.local
   ```
   Then edit `.env` and set:
   ```env
   NVIDIA_API_KEY=your_nvidia_api_key_here
   BACKEND_BASE_URL=http://localhost:8000
   ```

4. Update the video path in `anpr_video.py` to match your local file:
   ```python
   VIDEO_PATH = "path/to/your/video.mp4"
   ```

5. Run the pipeline:
   ```bash
   python anpr_video.py
   ```

## Sending events to the dashboard backend

The project includes a helper utility in `event_client.py` for sending vehicle/OCR data to your FastAPI backend.

### Example

```python
from event_client import send_vehicle_event

send_vehicle_event(
    camera_id="CAM01",
    plate_text="KA05AB1234",
    ocr_confidence=0.97,
    vehicle_class="SUV",
    vehicle_color="White",
    embedding=[0.142, -0.052, 0.811],
    plate_crop_url="https://example.com/plate_crop.jpg",
    base_url="http://localhost:8000",
)
```

This sends the payload to:

```http
POST http://localhost:8000/api/v1/events
```

with JSON headers and a timestamp automatically generated in UTC if not provided.

## Payload fields

The function accepts:

- `camera_id` (required)
- `plate_text` (required)
- `ocr_confidence` (required)
- `timestamp` (optional; auto-generated if missing)
- `vehicle_class` (optional)
- `vehicle_color` (optional)
- `embedding` (optional list of floats)
- `plate_crop_url` (optional)

## Notes

- The `.env` file is included in `.gitignore` and should never be committed.
- Do not hardcode secret keys in source files.
- The OCR model expects a valid NVIDIA API key with access to the configured vision endpoint.
- The backend should be running before sending events; the client will time out after 3 seconds if the service is unavailable.

## Requirements

The project uses:

- OpenCV
- NumPy
- python-dotenv
- Ultralytics YOLO
- Requests
