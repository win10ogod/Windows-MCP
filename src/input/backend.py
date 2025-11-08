from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from shutil import which
import logging
import subprocess
import tempfile
import textwrap
import os
import ctypes
from ctypes import wintypes
import ctypes
from ctypes import wintypes


@dataclass
class BackendInfo:
    name: str
    ready: bool
    details: str = ""


logger = logging.getLogger(__name__)


def _find_ahk_exe() -> str | None:
    """Locate AutoHotkey v2 executable.

    Order:
    - Respect explicit env var `AUTOHOTKEY_EXE`
    - Search PATH for common AHK executables
    - Probe typical installation paths on Windows
    """
    env = os.getenv("AUTOHOTKEY_EXE")
    if env and Path(env).exists():
        return env

    for name in ("AutoHotkey64.exe", "AutoHotkeyU64.exe", "AutoHotkey.exe", "autohotkey.exe"):
        exe = which(name)
        if exe:
            return exe

    # Typical Windows install locations
    candidates = []
    pf = os.environ.get("ProgramFiles", r"C:\\Program Files")
    pfx86 = os.environ.get("ProgramFiles(x86)", r"C:\\Program Files (x86)")
    for base in (pf, pfx86):
        candidates.extend([
            Path(base) / "AutoHotkey" / "v2" / "AutoHotkey64.exe",
            Path(base) / "AutoHotkey" / "AutoHotkey64.exe",
            Path(base) / "AutoHotkey" / "v2" / "AutoHotkeyU64.exe",
            Path(base) / "AutoHotkey" / "AutoHotkeyU64.exe",
            Path(base) / "AutoHotkey" / "v2" / "AutoHotkey.exe",
            Path(base) / "AutoHotkey" / "AutoHotkey.exe",
        ])
    for c in candidates:
        if c.exists():
            return str(c)

    return None


def _ib_ahk_include_path() -> Path:
    # Repo root: two levels up from this file (src/input/backend.py)
    return (Path(__file__).resolve().parents[2] / "IbInputSimulator" / "Binding.AHK2" / "IbInputSimulator.ahk")


def _ib_dll_path() -> Path:
    return (Path(__file__).resolve().parents[2] / "IbInputSimulator" / "Binding.AHK2" / "IbInputSimulator.dll")


class InputBackend:
    def info(self) -> BackendInfo:  # pragma: no cover
        raise NotImplementedError

    # Mouse
    def move(self, x: int, y: int):  # pragma: no cover
        raise NotImplementedError

    def click(self, x: int, y: int, button: str = "left", clicks: int = 1):  # pragma: no cover
        raise NotImplementedError

    def drag(self, x1: int, y1: int, x2: int, y2: int):  # pragma: no cover
        raise NotImplementedError

    # Keyboard
    def send_text(self, text: str):  # pragma: no cover
        raise NotImplementedError

    def hotkey(self, combo: str):  # e.g., "ctrl+c"
        raise NotImplementedError


class IBSimulatorAHKBackend(InputBackend):
    def __init__(self, driver: str = "AnyDriver"):
        self._ahk = _find_ahk_exe()
        self._inc = _ib_ahk_include_path()
        self._dll = _ib_dll_path()
        self._driver = driver
        self._ready = bool(self._ahk and self._inc.exists() and self._dll.exists())

    def info(self) -> BackendInfo:
        details = f"ahk={self._ahk}, include={self._inc}, dll={self._dll}"
        return BackendInfo("IBSimulatorAHK", self._ready, details)

    def _run(self, body: str) -> int:
        if not self._ready:
            return 1
        # Use Windows-style absolute paths for AHK includes and DLL loading
        inc_path = str(self._inc)
        dll_path = str(self._dll)

        hdr = textwrap.dedent(f"""
        #Requires AutoHotkey v2.0
        #NoTrayIcon
        SetBatchLines -1
        #DllLoad "*i {dll_path}"
        #Include "{inc_path}"
        try {{
            IbSendInit("{self._driver}")
        }} catch e {{
            try {{
                IbSendInit("SendInput")
            }} catch e2 {{
                SendMode "Input"
            }}
        }}
        ; Ensure absolute screen coordinates for all mouse ops
        CoordMode "Mouse", "Screen"
        CoordMode "Pixel", "Screen"
        """)
        script = hdr + "\n" + body + "\nExitApp\n"
        with tempfile.NamedTemporaryFile(prefix="ibsim_", suffix=".ahk", delete=False) as tf:
            tf.write(script.encode("utf-8"))
            tf_path = tf.name
        try:
            # Route AHK runtime errors to stdio (avoid blocking error dialogs)
            proc = subprocess.run([self._ahk, "/ErrorStdOut", tf_path], timeout=6)
            return proc.returncode
        finally:
            try:
                os.remove(tf_path)
            except Exception:
                pass

    def move(self, x: int, y: int):
        body = (
            "try {\n"
            f"    IbMouseMove {x}, {y}, 0\n"
            "} catch e {\n"
            f"    MouseMove {x}, {y}, 0\n"
            "}" 
        )
        self._run(body)

    def click(self, x: int, y: int, button: str = "left", clicks: int = 1):
        btn = button.lower()
        body = (
            "try {\n"
            f"    IbMouseClick \"{btn}\", {x}, {y}, {clicks}, 0\n"
            "} catch e {\n"
            f"    MouseClick \"{btn}\", {x}, {y}, {clicks}, 0\n"
            "}"
        )
        self._run(body)

    def drag(self, x1: int, y1: int, x2: int, y2: int):
        body = (
            "try {\n"
            f"    IbMouseClickDrag \"left\", {x1}, {y1}, {x2}, {y2}, 0\n"
            "} catch e {\n"
            f"    MouseClickDrag \"left\", {x1}, {y1}, {x2}, {y2}, 0\n"
            "}"
        )
        self._run(body)

    def send_text(self, text: str):
        """Send literal text without interpreting special characters.

        Use AHK's Send in {Text} mode while IbSendMode is active so input is
        injected via the configured driver. Double any embedded double quotes
        to satisfy AHK's string literal rules.
        """
        # AHK v2 doubles quotes to escape them inside string literals
        esc = text.replace('"', '""')
        body = (
            "try {\n"
            "    IbSendMode(1)\n"
            f"    Send(\"{{Text}}\" . \"{esc}\")\n"
            "    IbSendMode(0)\n"
            "} catch e {\n"
            "    SendMode \"Input\"\n"
            f"    Send(\"{{Text}}\" . \"{esc}\")\n"
            "}"
        )
        self._run(body)

    def hotkey(self, combo: str):
        """Send a hotkey/shortcut combination.

        Examples:
        - "ctrl+c"      -> ^c
        - "win+r"       -> #r
        - "ctrl+enter"  -> ^{Enter}
        - "backspace"    -> {Backspace}
        - "shift+tab"    -> +{Tab}
        """
        parts = [p.strip().lower() for p in combo.split("+") if p.strip()]
        mod_map = {"ctrl": "^", "alt": "!", "shift": "+", "win": "#"}
        # Normalize some common key names to AHK canonical names
        key_name_map = {
            "enter": "Enter",
            "return": "Enter",
            "backspace": "Backspace",
            "bs": "Backspace",
            "delete": "Delete",
            "del": "Delete",
            "insert": "Insert",
            "ins": "Insert",
            "tab": "Tab",
            "esc": "Escape",
            "escape": "Escape",
            "space": "Space",
            "home": "Home",
            "end": "End",
            "pgup": "PgUp",
            "pageup": "PgUp",
            "pgdn": "PgDn",
            "pagedown": "PgDn",
            "up": "Up",
            "down": "Down",
            "left": "Left",
            "right": "Right",
        }

        mods = []
        key = None
        for p in parts:
            if p in mod_map:
                mods.append(mod_map[p])
            elif len(p) == 1:  # single character key
                key = p
            else:
                key = "{" + key_name_map.get(p, p.capitalize()) + "}"

        if key is None:
            # Allow pure modifier taps like "win" if requested
            # Treat as pressing the modifier key itself
            if mods:
                # Map back to AHK key names for solitary modifier press
                back_map = {"^": "{Ctrl}", "!": "{Alt}", "+": "{Shift}", "#": "{LWin}"}
                key = back_map.get(mods[-1], "")
                mods = mods[:-1]
            else:
                key = ""

        ahk_seq = "".join(mods) + (key or "")
        body = (
            "try {\n"
            f"    IbSend(\"{ahk_seq}\")\n"
            "} catch e {\n"
            f"    Send(\"{ahk_seq}\")\n"
            "}"
        )
        self._run(body)


class PyAutoGUIBackend(InputBackend):
    def __init__(self):
        import pyautogui as pg
        self.pg = pg
        # Virtual screen metrics (for multi-monitor with negative origins)
        self._user32 = ctypes.windll.user32
        self._SM_XVIRTUALSCREEN = 76
        self._SM_YVIRTUALSCREEN = 77

    def info(self) -> BackendInfo:
        return BackendInfo("PyAutoGUI", True, f"failsafe={self.pg.FAILSAFE}")

    def move(self, x: int, y: int):
        # Adjust for virtual screen origin to avoid negative coords clamping
        left = self._user32.GetSystemMetrics(self._SM_XVIRTUALSCREEN)
        top = self._user32.GetSystemMetrics(self._SM_YVIRTUALSCREEN)
        self.pg.moveTo(int(x - left), int(y - top), duration=0.1)

    def click(self, x: int, y: int, button: str = "left", clicks: int = 1):
        left = self._user32.GetSystemMetrics(self._SM_XVIRTUALSCREEN)
        top = self._user32.GetSystemMetrics(self._SM_YVIRTUALSCREEN)
        self.pg.click(int(x - left), int(y - top), button=button, clicks=clicks, duration=0.1)

    def drag(self, x1: int, y1: int, x2: int, y2: int):
        left = self._user32.GetSystemMetrics(self._SM_XVIRTUALSCREEN)
        top = self._user32.GetSystemMetrics(self._SM_YVIRTUALSCREEN)
        self.pg.moveTo(int(x1 - left), int(y1 - top), duration=0.1)
        self.pg.dragTo(int(x2 - left), int(y2 - top), duration=0.6)

    def send_text(self, text: str):
        self.pg.typewrite(text, interval=0.02)

    def hotkey(self, combo: str):
        parts = [p.strip().lower() for p in combo.split("+") if p.strip()]
        if len(parts) > 1:
            self.pg.hotkey(*parts)
        else:
            self.pg.press(parts[0])


class IBSimulatorDLLBackend(InputBackend):
    def __init__(self, driver: str = "AnyDriver"):
        self._driver = driver
        self._debug = str(os.getenv('WINDOWS_MCP_INPUT_DEBUG', '0')).lower() in ('1','true','yes','on')
        base = Path(__file__).resolve().parents[2] / "IbInputSimulator"
        p1 = base / "Binding.AHK2" / "IbInputSimulator.dll"
        p2 = base / "IbInputSimulator.dll"
        self._dll_path = str(p1 if p1.exists() else p2)
        self._ready = False
        self._err = ""
        try:
            if not self._dll_path or not Path(self._dll_path).exists():
                self._err = f"dll not found at {self._dll_path}"
                return
            self._dll = ctypes.WinDLL(self._dll_path)
            # Prototypes
            self._dll.IbSendInit.argtypes = [ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p]
            self._dll.IbSendInit.restype = ctypes.c_uint32
            self._dll.IbSendDestroy.argtypes = []
            self._dll.IbSendDestroy.restype = None

            self._dll.IbSendMouseMove.argtypes = [ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32]
            self._dll.IbSendMouseMove.restype = ctypes.c_bool
            self._dll.IbSendMouseClick.argtypes = [ctypes.c_uint32]
            self._dll.IbSendMouseClick.restype = ctypes.c_bool
            self._dll.IbSendMouseWheel.argtypes = [ctypes.c_int32]
            self._dll.IbSendMouseWheel.restype = ctypes.c_bool

            self._dll.IbSendKeybdDown.argtypes = [ctypes.c_uint16]
            self._dll.IbSendKeybdDown.restype = ctypes.c_bool
            self._dll.IbSendKeybdUp.argtypes = [ctypes.c_uint16]
            self._dll.IbSendKeybdUp.restype = ctypes.c_bool

            # Initialize selected driver
            send_type = {
                "AnyDriver": 0,
                "SendInput": 1,
                "Logitech": 2,
                "Razer": 3,
                "DD": 4,
                "MouClassInputInjection": 5,
                "LogitechGHubNew": 6,
            }.get(self._driver, 0)
            rc = self._dll.IbSendInit(send_type, 0, None)
            if rc != 0:
                self._err = f"IbSendInit error={rc} (driver={self._driver})"
                return

            # user32 helpers
            self._user32 = ctypes.WinDLL('user32', use_last_error=True)
            self._user32.VkKeyScanW.argtypes = [wintypes.WCHAR]
            self._user32.VkKeyScanW.restype = ctypes.c_short
            self._user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
            self._user32.SetCursorPos.restype = ctypes.c_bool

            self._ready = True
        except Exception as e:
            self._err = str(e)
            self._ready = False

    def info(self) -> BackendInfo:
        return BackendInfo("IBSimulatorDLL", self._ready, f"dll={self._dll_path}, driver={self._driver}, err={self._err}")

    # Mouse
    def move(self, x: int, y: int):
        if not self._ready:
            return
        # First try OS absolute move (pixel accurate)
        xi, yi = int(x), int(y)
        self._user32.SetCursorPos(xi, yi)
        # Verify and correct with relative move if needed
        class POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
        pt = POINT()
        self._user32.GetCursorPos(ctypes.byref(pt))
        if self._debug:
            logger.info(f"DLL.move requested=({xi},{yi}) after SetCursorPos pos=({pt.x},{pt.y})")
        dx = xi - int(pt.x)
        dy = yi - int(pt.y)
        if dx or dy:
            # Attempt relative correction in one shot
            self._dll.IbSendMouseMove(ctypes.c_uint32(dx & 0xFFFFFFFF).value,
                                      ctypes.c_uint32(dy & 0xFFFFFFFF).value,
                                      1)  # Relative
            # Re-check once
            self._user32.GetCursorPos(ctypes.byref(pt))
            if self._debug:
                logger.info(f"DLL.move corrected by rel ({dx},{dy}) -> pos=({pt.x},{pt.y})")

    def click(self, x: int, y: int, button: str = "left", clicks: int = 1):
        if not self._ready:
            return
        self.move(x, y)
        btn_map = {
            'left': 0x06,   # LeftDown|LeftUp
            'right': 0x18,  # RightDown|RightUp
            'middle': 0x60, # MiddleDown|MiddleUp
        }
        code = btn_map.get(button.lower(), 0x06)
        for _ in range(max(1, int(clicks))):
            self._dll.IbSendMouseClick(code)

    def drag(self, x1: int, y1: int, x2: int, y2: int):
        if not self._ready:
            return
        self.move(x1, y1)
        self._dll.IbSendMouseClick(0x02)  # LeftDown
        self.move(x2, y2)
        self._dll.IbSendMouseClick(0x04)  # LeftUp

    # Keyboard
    def _vk_for_key(self, key: str) -> int | None:
        k = key.lower()
        special = {
            'enter': 0x0D, 'return': 0x0D, 'backspace': 0x08, 'tab': 0x09,
            'esc': 0x1B, 'escape': 0x1B, 'space': 0x20,
            'left': 0x25, 'up': 0x26, 'right': 0x27, 'down': 0x28,
            'home': 0x24, 'end': 0x23, 'insert': 0x2D, 'delete': 0x2E,
            'pgup': 0x21, 'pageup': 0x21, 'pgdn': 0x22, 'pagedown': 0x22,
            'f1': 0x70, 'f2': 0x71, 'f3': 0x72, 'f4': 0x73, 'f5': 0x74, 'f6': 0x75,
            'f7': 0x76, 'f8': 0x77, 'f9': 0x78, 'f10': 0x79, 'f11': 0x7A, 'f12': 0x7B,
        }
        if k in special:
            return special[k]
        if len(k) == 1:
            ch = k
            if 'a' <= ch <= 'z':
                return ord(ch.upper())
            if '0' <= ch <= '9':
                return ord(ch)
        return None

    def send_text(self, text: str):
        if not self._ready:
            return
        SHIFT = 0x10
        for ch in text:
            vkshort = self._user32.VkKeyScanW(ch)
            if vkshort == -1:
                continue
            vk = vkshort & 0xFF
            mods = (vkshort >> 8) & 0xFF
            try:
                if mods & 0x01: self._dll.IbSendKeybdDown(SHIFT)
                if mods & 0x02: self._dll.IbSendKeybdDown(0x11)  # CTRL
                if mods & 0x04: self._dll.IbSendKeybdDown(0x12)  # ALT
                self._dll.IbSendKeybdDown(vk)
                self._dll.IbSendKeybdUp(vk)
            finally:
                if mods & 0x04: self._dll.IbSendKeybdUp(0x12)
                if mods & 0x02: self._dll.IbSendKeybdUp(0x11)
                if mods & 0x01: self._dll.IbSendKeybdUp(SHIFT)

    def hotkey(self, combo: str):
        if not self._ready:
            return
        parts = [p.strip().lower() for p in combo.split('+') if p.strip()]
        mods = set()
        key = None
        for p in parts:
            if p in ("ctrl", "control"): mods.add("ctrl"); continue
            if p in ("alt",): mods.add("alt"); continue
            if p in ("shift",): mods.add("shift"); continue
            if p in ("win", "lwin", "rwin"): mods.add("win"); continue
            key = p
        if "win" in mods: self._dll.IbSendKeybdDown(0x5B)
        if "ctrl" in mods: self._dll.IbSendKeybdDown(0x11)
        if "alt" in mods: self._dll.IbSendKeybdDown(0x12)
        if "shift" in mods: self._dll.IbSendKeybdDown(0x10)
        if key:
            vk = self._vk_for_key(key)
            if vk is None and len(key) == 1:
                vkshort = self._user32.VkKeyScanW(key)
                vk = vkshort & 0xFF if vkshort != -1 else None
            if vk is not None:
                self._dll.IbSendKeybdDown(vk)
                self._dll.IbSendKeybdUp(vk)
        if "shift" in mods: self._dll.IbSendKeybdUp(0x10)
        if "alt" in mods: self._dll.IbSendKeybdUp(0x12)
        if "ctrl" in mods: self._dll.IbSendKeybdUp(0x11)
        if "win" in mods: self._dll.IbSendKeybdUp(0x5B)


def build_backend(preferred: str = "ibsim", driver: str = "AnyDriver") -> InputBackend:
    pref = (preferred or "").lower()
    # ibsim/ibsim-dll: try DLL first
    if pref in ("ibsim", "ibsim-dll"):
        try:
            dll = IBSimulatorDLLBackend(driver=driver)
            dinfo = dll.info()
            if dinfo.ready:
                return dll
            logger.warning(f"IBSimulator DLL backend not ready. Details: {dinfo.details}")
        except Exception as e:
            logger.warning(f"IBSimulator DLL backend init error: {e}")
        # For plain 'ibsim' we fall back to PyAutoGUI (skip AHK to avoid timeouts)
        if pref == "ibsim":
            return PyAutoGUIBackend()

    # Explicit AHK preference
    if pref == "ibsim-ahk":
        ahk = IBSimulatorAHKBackend(driver=driver)
        ainfo = ahk.info()
        if ainfo.ready:
            return ahk
        logger.warning(f"IBSimulator AHK backend not ready. Details: {ainfo.details}")
        return PyAutoGUIBackend()

    # Explicit PyAutoGUI or final fallback
    if pref == "pyautogui":
        return PyAutoGUIBackend()

    # Final fallback
    return PyAutoGUIBackend()


## Note: IBSimulatorDLLBackend is defined above. Remove duplicate definitions.
