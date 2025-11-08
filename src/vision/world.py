from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Tuple
from PIL import Image as PILImage, ImageDraw, ImageFont
from .schemas import Detection, Detections, BBox
import logging
import io
import os
import contextlib


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('[%(levelname)s] %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


@dataclass
class BackendInfo:
    name: str
    loaded: bool
    details: str = ""


class VisionDetector:
    """Pluggable detector with robust standard YOLO default and optional YOLO‑World.

    Behavior:
    - If `world_only=True`, try YOLO‑World first; otherwise prefer standard YOLO.
    - Resolves model paths from common directories or lets Ultralytics download.
    - Redirects Ultralytics stdout to stderr to keep MCP stdio clean.
    """

    def __init__(self, model: Optional[str] = None, world_only: bool = False):
        self.backend: BackendInfo
        self._model = None
        self._init_backend(model, world_only)

    def _model_dirs(self) -> list[str]:
        dirs = [
            ".",
            "./models",
            os.path.dirname(os.path.abspath(__file__)),
            os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../")),
        ]
        extra = os.getenv('WINDOWS_MCP_VISION_MODEL_DIRS')
        if extra:
            for p in extra.split(os.pathsep):
                p = p.strip()
                if p:
                    dirs.append(p)
        return dirs

    def _resolve_model_path(self, name: str) -> str:
        # Find file on disk or return name as-is (Ultralytics may download)
        for d in self._model_dirs():
            cand = os.path.join(d, name)
            if os.path.exists(cand):
                return cand
        return name

    @staticmethod
    def _is_world_weight(name: str | None) -> bool:
        return bool(name and ('world' in name.lower()))

    def _init_backend(self, model: Optional[str], world_only: bool):
        # Decide preferred order
        try_standard_first = not world_only

        if try_standard_first:
            # 1) Try standard YOLO
            try:
                with redirect_stdout_to_stderr():
                    from ultralytics import YOLO  # type: ignore
                    # Use a sensible default if model looks like a YOLO‑World weight
                    if model is None or self._is_world_weight(model):
                        name = os.getenv('WINDOWS_MCP_VISION_MODEL_STD', 'yolov8n.pt')
                    else:
                        name = model
                    name = self._resolve_model_path(name)
                    self._model = YOLO(name)
                self.backend = BackendInfo('yolo', True, f'model={name}')
                logger.info(f"Loaded YOLO backend: {name}")
                return
            except Exception as e:
                logger.info(f"YOLO unavailable: {e}")

        # 2) Try YOLO‑World
        try:
            with redirect_stdout_to_stderr():
                from ultralytics import YOLOWorld  # type: ignore
                name = model or os.getenv('WINDOWS_MCP_VISION_MODEL', 'yolov8s-world.pt')
                # Ensure a YOLO-World weight; override if user provided a non-world model
                if not self._is_world_weight(name):
                    logger.info(f"Requested YOLO-World but model '{name}' is not a *-world*. Using 'yolov8s-world.pt'.")
                    name = 'yolov8s-world.pt'
                name = self._resolve_model_path(name)
                self._model = YOLOWorld(name)
            self.backend = BackendInfo('yolo_world', True, f'model={name}')
            logger.info(f"Loaded YOLO-World backend: {name}")
            return
        except Exception as e:
            logger.info(f"YOLO-World unavailable: {e}")

        if world_only:
            self.backend = BackendInfo('none', False, 'YOLO-World required but not available')
            return

        # 3) If we tried world and standard already, emit final failure
        self.backend = BackendInfo('none', False, 'Install ultralytics and torch (standard) or extras for YOLO‑World')

    def detect(self, image: PILImage, prompts: Optional[List[str]] = None,
               conf: float = 0.25, iou: float = 0.45, max_det: int = 50,
               imgsz: Optional[int] = None, region: Optional[Tuple[int,int,int,int]] = None) -> Detections:
        if not self.backend.loaded:
            logger.warning("No vision backend available. Install: uv add ultralytics torch")
            return Detections([])

        # Convert image to a compatible format (RGB)
        if image.mode != 'RGB':
            image = image.convert('RGB')

        # Crop to region (l,t,r,b) if provided
        base_offset = (0, 0)
        if region and len(region) == 4:
            l, t, r, b = region
            l = max(0, l); t = max(0, t)
            r = min(image.width, r); b = min(image.height, b)
            image = image.crop((l, t, r, b))
            base_offset = (l, t)

        try:
            with redirect_stdout_to_stderr():
                sz = imgsz or int(os.getenv('WINDOWS_MCP_VISION_IMGSZ', '640') or '640')
                if self.backend.name == 'yolo_world':
                    # Only set classes if provided via tool args or env; otherwise use built-in offline vocab (COCO80)
                    use_prompts = None
                    if prompts and isinstance(prompts, list) and len(prompts) > 0:
                        use_prompts = prompts
                    elif os.getenv('WINDOWS_MCP_VISION_PROMPTS'):
                        env_p = os.getenv('WINDOWS_MCP_VISION_PROMPTS')
                        use_prompts = [p.strip() for p in env_p.split(',') if p.strip()]
                    if use_prompts:
                        self._model.set_classes(use_prompts)
                # Let Ultralytics handle resizing; results are returned in original image coords
                kwargs = {"conf": conf, "iou": iou, "max_det": max_det, "verbose": False}
                if isinstance(sz, int) and sz > 0:
                    kwargs["imgsz"] = sz
                results = self._model.predict(image, **kwargs)
        except Exception as e:
            logger.error(f"Detection error: {e}")
            return Detections([])

        items: List[Detection] = []
        try:
            r0 = results[0]
            # Ultralytics results: r0.boxes.xyxy, r0.boxes.conf, r0.boxes.cls, r0.names
            xyxy = r0.boxes.xyxy.cpu().numpy().tolist() if hasattr(r0.boxes.xyxy, 'cpu') else r0.boxes.xyxy
            confs = r0.boxes.conf.cpu().numpy().tolist() if hasattr(r0.boxes.conf, 'cpu') else r0.boxes.conf
            clss = r0.boxes.cls.cpu().numpy().tolist() if hasattr(r0.boxes.cls, 'cpu') else r0.boxes.cls
            names = r0.names
            for (x1, y1, x2, y2), c, k in zip(xyxy, confs, clss):
                try:
                    label = names[int(k)] if isinstance(names, dict) else str(k)
                except Exception:
                    label = str(k)
                bx1, by1, bx2, by2 = int(x1), int(y1), int(x2), int(y2)
                # add region base offset if cropped
                if base_offset != (0, 0):
                    bx1 += base_offset[0]; bx2 += base_offset[0]
                    by1 += base_offset[1]; by2 += base_offset[1]
                items.append(Detection(label=label, score=float(c), bbox=BBox(bx1, by1, bx2, by2)))
        except Exception as e:
            logger.error(f"Result parsing error: {e}")
            return Detections([])

        return Detections(items)

    @staticmethod
    def visualize(image: PILImage, detections: Detections) -> PILImage:
        img = image.copy()
        draw = ImageDraw.Draw(img)
        # Optional: Try to load a default font
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None

        def measure(text: str) -> tuple[int, int]:
            # Prefer modern Pillow API
            try:
                bbox = draw.textbbox((0, 0), text, font=font)
                return bbox[2] - bbox[0], bbox[3] - bbox[1]
            except Exception:
                pass
            # Fallback to legacy API if available
            try:
                return draw.textsize(text, font=font)  # type: ignore[attr-defined]
            except Exception:
                pass
            # Safe fallback estimate
            return 8 * len(text), 12

        if not detections.items:
            # Draw a small banner to indicate pipeline ran but found nothing
            msg = "No detections"
            tw, th = measure(msg)
            draw.rectangle([2, 2, 10 + tw, 8 + th], fill=(0, 0, 0))
            draw.text((6, 4), msg, fill=(255, 255, 255), font=font)
            return img

        for d in detections.items:
            x1, y1, x2, y2 = d.bbox.x1, d.bbox.y1, d.bbox.x2, d.bbox.y2
            draw.rectangle([x1, y1, x2, y2], outline=(255, 0, 0), width=2)
            text = f"{d.label} {d.score:.2f}"
            tw, th = measure(text)
            # Place label above box if space, else below
            label_top = y1 - th - 2
            if label_top < 0:
                label_top = y1 + 2
            draw.rectangle([x1, label_top, x1 + tw + 4, label_top + th + 2], fill=(255, 0, 0))
            draw.text((x1 + 2, label_top + 1), text, fill=(255, 255, 255), font=font)
        return img

    @staticmethod
    def to_png_bytes(image: PILImage) -> bytes:
        bio = io.BytesIO()
        image.save(bio, format='PNG')
        return bio.getvalue()


@contextlib.contextmanager
def redirect_stdout_to_stderr():
    """Redirect Ultralytics prints to stderr (preserves visibility; avoids MCP stdout).

    This mirrors YOLO-MCP-Server behavior to prevent stdout corruption while
    still allowing logs to appear on stderr.
    """
    old = os.dup(1)
    try:
        os.dup2(2, 1)  # dup stdout -> stderr
        yield
    finally:
        try:
            os.dup2(old, 1)
        except Exception:
            pass
        try:
            os.close(old)
        except Exception:
            pass
