#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

PYTHON_BIN="${PYTHON_BIN:-/Users/hyq/opt/anaconda3/envs/yt_pdf/bin/python}"
YTDLP_BIN="${YTDLP_BIN:-/Users/hyq/opt/anaconda3/envs/yt_pdf/bin/yt-dlp}"
FFMPEG_BIN="${FFMPEG_BIN:-/Users/hyq/opt/anaconda3/envs/yt_pdf/bin/ffmpeg}"
WHISPER_BIN="${WHISPER_BIN:-/Users/hyq/opt/anaconda3/envs/yt_pdf/bin/whisper}"
MAGICK_BIN="${MAGICK_BIN:-/opt/homebrew/bin/magick}"

TEST_URL="${TEST_URL:-https://www.youtube.com/watch?v=lTcOkFg4geg}"
WORK_DIR="${WORK_DIR:-$ROOT_DIR/work/test-youtube-smoke}"
FRAME_INTERVAL="${FRAME_INTERVAL:-30}"
WHISPER_MODEL="${WHISPER_MODEL:-small}"
FRAMES_FOR_NOTES="${FRAMES_FOR_NOTES:-01:00,02:30,04:30}"

echo "[1/8] workspace: $WORK_DIR"
mkdir -p "$WORK_DIR"
cd "$WORK_DIR"
mkdir -p subtitles frames

echo "[2/8] metadata + cover + subtitle probe"
"$YTDLP_BIN" \
  --write-info-json \
  --write-thumbnail \
  --write-subs \
  --write-auto-subs \
  --sub-langs "zh.*,en.*" \
  --convert-subs srt \
  --skip-download \
  -o "%(title)s.%(ext)s" \
  "$TEST_URL"

echo "[3/8] extract audio wav"
"$YTDLP_BIN" \
  -x \
  --audio-format wav \
  -o "audio.%(ext)s" \
  "$TEST_URL"

echo "[4/8] whisper transcript"
"$WHISPER_BIN" \
  audio.wav \
  --model "$WHISPER_MODEL" \
  --output_format srt \
  --output_dir subtitles

echo "[5/8] download 720p video"
"$YTDLP_BIN" \
  -f "bv*[height<=720]+ba/b[height<=720]" \
  --merge-output-format mp4 \
  -o "video.%(ext)s" \
  "$TEST_URL"

echo "[6/8] extract frames (every ${FRAME_INTERVAL}s)"
"$FFMPEG_BIN" \
  -i video.mp4 \
  -vf "fps=1/${FRAME_INTERVAL},scale=1280:-1" \
  "frames/frame_%03d.jpg"

echo "[7/8] build contact sheet"
"$MAGICK_BIN" montage frames/*.jpg \
  -font Helvetica \
  -thumbnail 320x180 \
  -geometry +8+8 \
  contact_sheet.jpg

echo "[8/8] generate notes.tex and notes.pdf"
"$PYTHON_BIN" "$ROOT_DIR/scripts/smoke_generate_notes_pdf.py" \
  --workdir "$WORK_DIR" \
  --env "$ROOT_DIR/.env" \
  --frames "$FRAMES_FOR_NOTES" \
  --frame-interval "$FRAME_INTERVAL" \
  --magick "$MAGICK_BIN"

echo "Smoke test finished."
echo "Output: $WORK_DIR/notes.pdf"
