from __future__ import annotations

import os
import subprocess
import tempfile
from io import BytesIO
from pathlib import Path
from typing import Optional, Tuple

from PIL import Image, ImageOps, UnidentifiedImageError

SUPPORTED_IMAGE_FORMATS = {
    "JPEG": ".jpg",
    "PNG": ".png",
    "WEBP": ".webp",
    "GIF": ".gif",
    "BMP": ".bmp",
}
HEIC_EXTENSIONS = {".heic", ".heif"}
SIPS_PATH = Path("/usr/bin/sips")
EXTENSION_TO_MEDIA_TYPE = {
    ".jpg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
}

# Server-side safety net: always compress non-GIF images to stay within limits
_MAX_DIMENSION = 800
_MAX_SIZE_BYTES = 200 * 1024  # 200 KB


def prepare_uploaded_image(filename: Optional[str], content: bytes) -> Tuple[bytes, str]:
    if not content:
        raise ValueError("上传的图片为空")

    extension = _normalize_extension(filename)
    if extension in HEIC_EXTENSIONS:
        return _convert_heic_to_jpeg(content, extension), ".jpg"

    detected_format = _detect_image_format(content)
    if detected_format not in SUPPORTED_IMAGE_FORMATS:
        raise ValueError("仅支持 JPG、PNG、WEBP、GIF、BMP 或 HEIC 图片")

    # Always compress non-GIF images server-side to enforce dimension/size limits
    if detected_format != "GIF":
        compressed = _compress_image(content)
        if compressed:
            return compressed, ".jpg"

    return content, SUPPORTED_IMAGE_FORMATS[detected_format]


def _compress_image(content: bytes) -> Optional[bytes]:
    """Resize to _MAX_DIMENSION on longest side and re-encode as JPEG."""
    try:
        with Image.open(BytesIO(content)) as image:
            normalized = ImageOps.exif_transpose(image)
            w, h = normalized.size
            if max(w, h) > _MAX_DIMENSION:
                scale = _MAX_DIMENSION / max(w, h)
                normalized = normalized.resize(
                    (int(w * scale), int(h * scale)), Image.LANCZOS
                )
            if normalized.mode != "RGB":
                normalized = normalized.convert("RGB")
            buffer = BytesIO()
            normalized.save(buffer, format="JPEG", quality=55, optimize=True)
            return buffer.getvalue()
    except Exception:
        return None


def media_type_for_extension(extension: str) -> str:
    return EXTENSION_TO_MEDIA_TYPE.get(extension.lower(), "application/octet-stream")


def _normalize_extension(filename: Optional[str]) -> str:
    extension = os.path.splitext(filename or "")[1].lower()
    if extension == ".jpeg":
        return ".jpg"
    return extension


def _detect_image_format(content: bytes) -> str:
    try:
        with Image.open(BytesIO(content)) as image:
            image.load()
            return (image.format or "").upper()
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("上传的文件不是可识别的图片") from exc


def _convert_heic_to_jpeg(content: bytes, extension: str) -> bytes:
    try:
        with Image.open(BytesIO(content)) as image:
            return _save_as_jpeg(image)
    except (UnidentifiedImageError, OSError):
        pass

    if not SIPS_PATH.exists():
        raise ValueError("当前环境暂不支持 HEIC/HEIF 图片，请上传 JPG 或 PNG")

    with tempfile.TemporaryDirectory() as tmp_dir:
        source_path = Path(tmp_dir) / f"source{extension}"
        output_path = Path(tmp_dir) / "converted.jpg"
        source_path.write_bytes(content)

        result = subprocess.run(
            [str(SIPS_PATH), "-s", "format", "jpeg", str(source_path), "--out", str(output_path)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0 or not output_path.exists():
            raise ValueError("HEIC 图片转换失败，请改用 JPG 或 PNG 后重试")

        return output_path.read_bytes()


def _save_as_jpeg(image: Image.Image) -> bytes:
    normalized = ImageOps.exif_transpose(image)
    if normalized.mode != "RGB":
        normalized = normalized.convert("RGB")

    buffer = BytesIO()
    normalized.save(buffer, format="JPEG", quality=92)
    return buffer.getvalue()
