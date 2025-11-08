from __future__ import annotations
from pathlib import Path
import os
import time


def ensure_output_dir() -> Path:
    """Resolve and create the output directory for saved images.

    Priority:
    1) WINDOWS_MCP_OUTPUT_DIR env var
    2) %LOCALAPPDATA%/Windows-MCP/outputs (Windows)
    3) %USERPROFILE%/Pictures/Windows-MCP
    4) Temp directory: %TEMP%/windows-mcp
    """
    env = os.getenv('WINDOWS_MCP_OUTPUT_DIR')
    if env:
        p = Path(env).expanduser().resolve()
    else:
        local = os.getenv('LOCALAPPDATA')
        if local:
            p = Path(local) / 'Windows-MCP' / 'outputs'
        else:
            home = Path(os.path.expanduser('~'))
            pictures = home / 'Pictures'
            if pictures.exists():
                p = pictures / 'Windows-MCP'
            else:
                from tempfile import gettempdir
                p = Path(gettempdir()) / 'windows-mcp'
    p.mkdir(parents=True, exist_ok=True)
    return p


def _unique_name(prefix: str, ext: str) -> str:
    ts = time.strftime('%Y%m%d_%H%M%S')
    return f"{prefix}_{ts}.{ext}"


def save_bytes(data: bytes, filename: str | None = None, prefix: str = 'image', ext: str = 'png') -> str:
    out_dir = ensure_output_dir()
    name = filename if filename else _unique_name(prefix, ext)
    if not name.lower().endswith(f'.{ext}'):
        name = f"{name}.{ext}"
    path = (out_dir / name).resolve()
    path.write_bytes(data)
    return str(path)

