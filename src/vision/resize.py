from __future__ import annotations
from typing import Tuple
from PIL import Image


def letterbox(img: Image.Image, size: int = 640, color=(114, 114, 114)) -> tuple[Image.Image, float, int, int]:
    """Resize and pad image to square 'size' keeping aspect ratio.

    Returns (padded_image, gain, pad_x, pad_y) where:
    - gain: scale factor from original -> resized
    - pad_x, pad_y: left/top padding applied on the square canvas
    """
    w, h = img.width, img.height
    if w == 0 or h == 0:
        return img, 1.0, 0, 0
    r = min(size / w, size / h)
    nw, nh = int(round(w * r)), int(round(h * r))
    # Resize
    resized = img.resize((nw, nh), Image.Resampling.LANCZOS)
    # Create canvas
    canvas = Image.new('RGB', (size, size), color)
    pad_x = (size - nw) // 2
    pad_y = (size - nh) // 2
    canvas.paste(resized, (pad_x, pad_y))
    return canvas, r, pad_x, pad_y


def map_box_back(x1: float, y1: float, x2: float, y2: float,
                 gain: float, pad_x: int, pad_y: int,
                 orig_w: int, orig_h: int) -> tuple[int, int, int, int]:
    # Reverse padding and scaling, then clamp
    ox1 = int(round((x1 - pad_x) / (gain if gain != 0 else 1)))
    oy1 = int(round((y1 - pad_y) / (gain if gain != 0 else 1)))
    ox2 = int(round((x2 - pad_x) / (gain if gain != 0 else 1)))
    oy2 = int(round((y2 - pad_y) / (gain if gain != 0 else 1)))
    ox1 = max(0, min(orig_w, ox1))
    oy1 = max(0, min(orig_h, oy1))
    ox2 = max(0, min(orig_w, ox2))
    oy2 = max(0, min(orig_h, oy2))
    return ox1, oy1, ox2, oy2

