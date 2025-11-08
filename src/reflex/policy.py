from __future__ import annotations
from dataclasses import dataclass
from typing import List, Protocol, Optional


@dataclass
class Action:
    kind: str  # 'move' | 'click' | 'shortcut'
    x: Optional[int] = None
    y: Optional[int] = None
    button: str = 'left'
    clicks: int = 1
    combo: Optional[str] = None  # e.g., 'ctrl+c'


class ReflexPolicy(Protocol):
    def predict(self, pil_image) -> List[Action]:
        ...


class NoOpPolicy:
    def predict(self, pil_image) -> List[Action]:
        return []


def load_policy(module_path: str, object_name: str) -> ReflexPolicy:
    mod = __import__(module_path, fromlist=[object_name])
    obj = getattr(mod, object_name)
    if isinstance(obj, type):
        return obj()  # construct
    return obj  # assume callable/policy instance

