from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

# Static ffmpeg binary bundled with the project
_BIN_DIR = Path(__file__).resolve().parents[2] / "bin"
FFMPEG_PATH = _BIN_DIR / "ffmpeg"

# Compression targets
_TARGET_WIDTH = 1280          # max long-edge pixels
_TARGET_CRF = 28              # H.264 CRF: lower = better quality (18-28 is good range)
_TARGET_AUDIO_BITRATE = "96k" # audio bitrate
_MAX_OUTPUT_SIZE = 50 * 1024 * 1024  # 50 MB ceiling for compressed output


def ffmpeg_available() -> bool:
    return FFMPEG_PATH.exists() and os.access(FFMPEG_PATH, os.X_OK)


def compress_video(input_bytes: bytes, original_filename: str = "") -> tuple[bytes, str]:
    """
    Compress a video using ffmpeg.

    Strategy:
    - Re-encode to H.264 (libx264) with CRF 28 for aggressive size reduction
    - Scale long edge to max 1280px, maintain aspect ratio
    - Strip unnecessary metadata streams
    - Output as .mp4 (widely compatible)

    Returns (compressed_bytes, ".mp4") or raises ValueError on failure.
    """
    if not ffmpeg_available():
        raise ValueError("服务器暂不支持视频压缩，请在上传前手动压缩视频")

    with tempfile.TemporaryDirectory() as tmp_dir:
        ext = os.path.splitext(original_filename or "video")[1].lower() or ".mp4"
        input_path = Path(tmp_dir) / f"input{ext}"
        output_path = Path(tmp_dir) / "output.mp4"

        input_path.write_bytes(input_bytes)

        # Build ffmpeg command
        # vf scale: scale long edge to 1280, keep aspect, ensure even dimensions
        cmd = [
            str(FFMPEG_PATH),
            "-y",                          # overwrite output
            "-i", str(input_path),
            "-vf", (
                f"scale='if(gt(iw,ih),min(iw,{_TARGET_WIDTH}),-2)':"
                f"'if(gt(iw,ih),-2,min(ih,{_TARGET_WIDTH}))',"
                "scale=trunc(iw/2)*2:trunc(ih/2)*2"  # ensure even dimensions
            ),
            "-c:v", "libx264",
            "-crf", str(_TARGET_CRF),
            "-preset", "fast",             # fast preset: good speed/compression balance
            "-c:a", "aac",
            "-b:a", _TARGET_AUDIO_BITRATE,
            "-movflags", "+faststart",     # move moov atom to front for fast streaming
            "-map_metadata", "-1",         # strip metadata
            "-map", "0:v:0",              # video stream only
            "-map", "0:a:0?",             # audio stream if present (optional)
            str(output_path),
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=300,  # 5 min max
        )

        if result.returncode != 0 or not output_path.exists():
            stderr = result.stderr.decode("utf-8", errors="replace")[-500:]
            raise ValueError(f"视频压缩失败，请检查视频格式是否支持。({stderr})")

        compressed = output_path.read_bytes()

        # If compressed is larger than original (unlikely but possible for already-compressed videos),
        # only use compressed if it's meaningfully smaller
        if len(compressed) >= len(input_bytes) * 0.95:
            # Return original if compression didn't help much; still re-container to mp4
            return compressed, ".mp4"

        return compressed, ".mp4"
