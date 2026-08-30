# SIH26-CODEZERO ANPR Pipeline

This project detects vehicles in a video, extracts number plates, reads them using NVIDIA Vision AI, and sends the final recognized plate to a backend API.

The goal is simple: a user can download this project, open a terminal, and run it without manually writing Python code.

## What this project does

- Detects vehicles from video frames
- Tracks each vehicle across frames
- Detects plates on each vehicle
- Uses NVIDIA Vision API to read the plate text
- Finalizes the most likely plate using a majority-vote approach
- Sends the result to the configured backend

## Files in this project

- `anpr_video.py` — main video processing pipeline
- `event_client.py` — sends detection events to the backend
- `model_check.py` — checks whether the model files are valid
- `vehiclemodelv8m.pt` — vehicle detection model
- `plate_model.pt` — license plate detection model
- `requirements.txt` — Python dependencies
- `.env` — local secrets such as the NVIDIA API key
- `test.mp4` — sample video used by the pipeline

## One-click setup for beginners

From the project folder, run these commands in your terminal:

```bash
cd /path/to/SIH26-CODEZERO
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python anpr_video.py
```

If the project is already set up and you only want to run it again:

```bash
cd /path/to/SIH26-CODEZERO
source .venv/bin/activate
python anpr_video.py
```

## Required environment variable

Before running the project, make sure your NVIDIA API key is present in `.env`:

```env
NVIDIA_API_KEY=your_api_key_here
```

If `.env` does not exist, create it with:

```bash
nano .env
```

Then paste:

```env
NVIDIA_API_KEY=your_api_key_here
```

## Run it with a single shell script

This project includes a helper script so you can run everything in one command:

```bash
chmod +x run.sh
./run.sh
```

This script will:

- create a virtual environment if missing
- install requirements
- load environment variables
- start the ANPR pipeline

## Change the input video

Open `anpr_video.py` and set the video file path:

```python
VIDEO_PATH = os.path.join(SCRIPT_DIR, "test.mp4")
```

You can replace `test.mp4` with any video file in the same folder, for example:

```python
VIDEO_PATH = os.path.join(SCRIPT_DIR, "my_vehicle_video.mp4")
```

## Backend URL configuration

The event sender uses a backend URL from the environment variable `BACKEND_BASE_URL` or falls back to the default value in `event_client.py`.

Example:

```env
BACKEND_BASE_URL=http://localhost:8000
```

## Troubleshooting

### 1. `NVIDIA_API_KEY not set`
This means your `.env` file is not loaded or is missing the key.

Fix:

```bash
nano .env
```

and add:

```env
NVIDIA_API_KEY=your_api_key_here
```

### 2. Python package errors
Run:

```bash
pip install -r requirements.txt
```

### 3. Video cannot be opened
Check that the file path in `anpr_video.py` is correct and that the video exists in the project folder.

### 4. No plate detected
This may happen if the video is too blurry, too dark, or the plate is not visible enough.

## Example workflow for a new user

```bash
git clone <repo-url>
cd SIH26-CODEZERO
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
nano .env
# add NVIDIA_API_KEY=your_api_key_here
python anpr_video.py
```

## Notes

- Do not hardcode API keys directly into source files.
- Keep `.env` local and private.
- The project expects NVIDIA access for the vision OCR model.
- The backend should be running if you want event submissions to be accepted.

## License

This project is for academic and local development use.
