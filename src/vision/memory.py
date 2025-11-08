from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, List
from .schemas import Detection


@dataclass
class Annotation:
    label: str
    bbox: list[int]  # [x1,y1,x2,y2]
    score: float | None = None

    @staticmethod
    def from_detection(d: Detection) -> "Annotation":
        return Annotation(label=d.label, bbox=[d.bbox.x1, d.bbox.y1, d.bbox.x2, d.bbox.y2], score=d.score)


class VisionMemory:
    """In-memory store for per-window annotations/detections.

    Keyed by top-level window handle (int). Values are lists of Annotation.
    """

    def __init__(self):
        self._store: Dict[int, List[Annotation]] = {}

    def set(self, handle: int, annotations: List[Annotation]):
        self._store[handle] = list(annotations)

    def append(self, handle: int, annotations: List[Annotation]):
        self._store.setdefault(handle, [])
        self._store[handle].extend(annotations)

    def get(self, handle: int) -> List[Annotation]:
        return list(self._store.get(handle, []))

    def clear(self, handle: int | None = None):
        if handle is None:
            self._store.clear()
        else:
            self._store.pop(handle, None)

    def to_serializable(self, handle: int) -> list[dict]:
        return [asdict(a) for a in self.get(handle)]

