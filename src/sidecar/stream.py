from __future__ import annotations
from dataclasses import dataclass
from threading import Thread, Event
from time import perf_counter, sleep
from typing import Optional, Tuple
from PIL import Image
import logging


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('[%(levelname)s] %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


@dataclass
class CaptureConfig:
    fps: int = 60
    region: Optional[Tuple[int, int, int, int]] = None  # left, top, right, bottom
    downscale: float = 1.0
    color: str = 'RGB'


class _DxgiGrabber:
    def __init__(self, region: Optional[Tuple[int, int, int, int]]):
        import dxcam  # type: ignore
        self._cam = dxcam.create(output_idx=0, device_idx=0, output_color="BGRA")
        self._region = region

    def grab(self) -> Image.Image:
        frame = self._cam.grab(region=self._region)
        # frame is BGRA numpy array
        from PIL import Image as PILImage
        img = PILImage.fromarray(frame, mode='BGRA').convert('RGB')
        return img


class _MSSGrabber:
    def __init__(self, region: Optional[Tuple[int, int, int, int]]):
        import mss  # type: ignore
        self._mss = mss.mss()
        self._region = region

    def grab(self) -> Image.Image:
        from PIL import Image as PILImage
        if self._region:
            l, t, r, b = self._region
            mon = {"left": l, "top": t, "width": r - l, "height": b - t}
        else:
            mon = self._mss.monitors[1]
        raw = self._mss.grab(mon)
        img = PILImage.frombytes('RGB', raw.size, raw.rgb)
        return img


class _PGGrabber:
    def __init__(self, region: Optional[Tuple[int, int, int, int]]):
        import pyautogui as pg
        self.pg = pg
        self._region = region

    def grab(self) -> Image.Image:
        if self._region:
            l, t, r, b = self._region
            w, h = r - l, b - t
            return self.pg.screenshot(region=(l, t, w, h))
        return self.pg.screenshot()


class FrameStream:
    def __init__(self):
        self._cfg: Optional[CaptureConfig] = None
        self._grabber = None
        self._latest: Optional[Image.Image] = None
        self._running = Event()
        self._thread: Optional[Thread] = None

    def _build_grabber(self, region) -> object:
        try:
            return _DxgiGrabber(region)
        except Exception as e:
            logger.info(f"DXGI (dxcam) unavailable: {e}")
        try:
            return _MSSGrabber(region)
        except Exception as e:
            logger.info(f"MSS unavailable: {e}")
        return _PGGrabber(region)

    def start(self, cfg: CaptureConfig):
        if self._running.is_set():
            return
        self._cfg = cfg
        self._grabber = self._build_grabber(cfg.region)
        self._running.set()
        self._thread = Thread(target=self._loop, name="FrameStream", daemon=True)
        self._thread.start()
        logger.info(f"FrameStream started: {cfg}")

    def stop(self):
        if not self._running.is_set():
            return
        self._running.clear()
        if self._thread:
            self._thread.join(timeout=1.0)
        logger.info("FrameStream stopped")

    def get_latest(self) -> Optional[Image.Image]:
        return self._latest

    def _loop(self):
        assert self._cfg is not None
        dt = 1.0 / max(1, int(self._cfg.fps))
        while self._running.is_set():
            t0 = perf_counter()
            try:
                img = self._grabber.grab()
                if self._cfg.downscale and self._cfg.downscale != 1.0:
                    w = int(img.width * self._cfg.downscale)
                    h = int(img.height * self._cfg.downscale)
                    img = img.resize((w, h), Image.Resampling.LANCZOS)
                if self._cfg.color.upper() == 'RGB' and img.mode != 'RGB':
                    img = img.convert('RGB')
                self._latest = img
            except Exception as e:
                logger.error(f"Capture error: {e}")
            # pace
            spend = perf_counter() - t0
            if spend < dt:
                sleep(dt - spend)

