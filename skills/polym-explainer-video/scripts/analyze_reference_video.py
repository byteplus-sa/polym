#!/usr/bin/env python3
"""
Analyze a user-provided reference video to extract style cues for storyboard design.

Outputs:
  - JSON metadata (duration, frame rate, resolution, cut count)
  - Key frames extracted to ./frames/ directory
  - audio.wav if audio is present (for optional transcription)

Usage:
    python3 analyze_reference_video.py path/to/reference.mp4
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def run(cmd, capture=True):
    return subprocess.run(cmd, capture_output=capture, text=True)


def probe(path):
    """ffprobe to get duration, codecs, dimensions."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration,bit_rate",
        "-show_entries", "stream=codec_type,codec_name,width,height,r_frame_rate,sample_rate",
        "-of", "json", str(path),
    ]
    r = run(cmd)
    if r.returncode != 0:
        print(f"ffprobe failed: {r.stderr}", file=sys.stderr)
        sys.exit(1)
    return json.loads(r.stdout)


def extract_key_frames(path, out_dir, count=6):
    """Extract `count` evenly spaced frames as JPGs."""
    out_dir.mkdir(exist_ok=True)
    duration = float(probe(path)["format"]["duration"])
    interval = duration / count
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-i", str(path),
        "-vf", f"fps=1/{interval},scale=480:-1",
        str(out_dir / "frame_%03d.jpg"),
    ]
    run(cmd, capture=False)
    return sorted(out_dir.glob("frame_*.jpg"))


def detect_cuts(path, threshold=0.3):
    """Approximate scene change detection via ffmpeg select filter."""
    cmd = [
        "ffmpeg", "-i", str(path),
        "-filter:v", f"select='gt(scene,{threshold})',showinfo",
        "-f", "null", "-",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    # showinfo lines appear in stderr
    return r.stderr.count("showinfo")


def extract_audio(path, out_wav):
    """Extract mono 16kHz wav if audio is present."""
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-i", str(path),
        "-ac", "1", "-ar", "16000",
        "-map", "0:a?", str(out_wav),
    ]
    r = run(cmd)
    return r.returncode == 0 and out_wav.exists() and out_wav.stat().st_size > 0


def parse_frame_rate(rfr):
    """Parse e.g. '30000/1001' or '30/1' to float."""
    if "/" in rfr:
        num, den = rfr.split("/")
        return round(float(num) / float(den), 2)
    return float(rfr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video", help="Path to reference video")
    ap.add_argument("--out-dir", default=".", help="Output directory for frames and metadata")
    args = ap.parse_args()

    video = Path(args.video).resolve()
    if not video.exists():
        print(f"ERROR: video not found: {video}", file=sys.stderr)
        sys.exit(1)

    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Analyzing {video.name}...", file=sys.stderr)

    info = probe(video)
    duration = float(info["format"]["duration"])

    video_stream = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    audio_stream = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)

    width = video_stream["width"] if video_stream else 0
    height = video_stream["height"] if video_stream else 0
    fps = parse_frame_rate(video_stream["r_frame_rate"]) if video_stream else 0

    aspect = "9:16" if height > width else ("16:9" if width > height else "1:1")

    # Extract frames
    frames_dir = out_dir / "frames"
    frame_count = max(4, min(8, int(duration / 2.5)))
    frames = extract_key_frames(video, frames_dir, count=frame_count)

    # Detect cuts
    cuts = detect_cuts(video)

    # Audio extraction
    audio_wav = out_dir / "audio.wav"
    has_audio = extract_audio(video, audio_wav) if audio_stream else False

    metadata = {
        "source": str(video),
        "duration_seconds": round(duration, 2),
        "frame_rate": fps,
        "resolution": f"{width}x{height}",
        "aspect_ratio": aspect,
        "estimated_cut_count": cuts,
        "average_shot_duration": round(duration / max(cuts, 1), 2),
        "key_frames_count": len(frames),
        "key_frames_path": str(frames_dir),
        "has_audio": has_audio,
        "audio_codec": audio_stream["codec_name"] if audio_stream else None,
        "audio_path": str(audio_wav) if has_audio else None,
    }

    out_json = out_dir / "reference_analysis.json"
    out_json.write_text(json.dumps(metadata, indent=2))

    print(json.dumps(metadata, indent=2))
    print(f"\nMetadata saved to {out_json}", file=sys.stderr)
    print(f"Key frames in {frames_dir}/", file=sys.stderr)
    if has_audio:
        print(f"Audio extracted to {audio_wav}", file=sys.stderr)
        print("Tip: run `npx hyperframes transcribe audio.wav` to get a transcript",
              file=sys.stderr)


if __name__ == "__main__":
    main()
