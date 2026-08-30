#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo "Creating Python virtual environment..."
  python3 -m venv .venv
fi

source .venv/bin/activate

echo "Upgrading pip..."
python -m pip install --upgrade pip >/dev/null

echo "Installing project dependencies..."
pip install -r requirements.txt

if [ ! -f ".env" ] && [ -f ".env.example" ]; then
  echo "Creating .env from template..."
  cp .env.example .env
fi

if [ -f ".env" ]; then
  set -a
  source .env
  set +a
fi

echo "Starting ANPR pipeline..."
python anpr_video.py
