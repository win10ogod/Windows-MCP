from dataclasses import dataclass, field
from typing import List


@dataclass
class BBox:
    x1: int
    y1: int
    x2: int
    y2: int

    def center(self) -> tuple[int, int]:
        return ((self.x1 + self.x2) // 2, (self.y1 + self.y2) // 2)

    def to_string(self) -> str:
        return f"({self.x1},{self.y1},{self.x2},{self.y2})"


@dataclass
class Detection:
    label: str
    score: float
    bbox: BBox

    def to_row(self) -> list:
        return [self.label, round(self.score, 3), self.bbox.to_string()]


@dataclass
class Detections:
    items: List[Detection] = field(default_factory=list)

    def to_table(self) -> str:
        try:
            from tabulate import tabulate
        except Exception:
            # Fallback plain formatting
            rows = ["label\tscore\tbbox"]
            rows += ["\t".join(map(str, d.to_row())) for d in self.items]
            return "\n".join(rows)
        headers = ["Label", "Score", "BBox(x1,y1,x2,y2)"]
        rows = [d.to_row() for d in self.items]
        return tabulate(rows, headers=headers, tablefmt="github")

