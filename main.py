from live_inspect.watch_cursor import WatchCursor
from contextlib import asynccontextmanager
from fastmcp.utilities.types import Image
import os
from src.desktop.service import Desktop
from humancursor import SystemCursor
from textwrap import dedent
from fastmcp import FastMCP
from typing import Literal
import base64
import pyautogui as pg
import asyncio
import click
import ctypes
from ctypes import wintypes

pg.FAILSAFE= (os.getenv('WINDOWS_MCP_PG_FAILSAFE','0').lower() in ['1','true','yes','on'])
try:
    pg.PAUSE=float(os.getenv('WINDOWS_MCP_PG_PAUSE','0.0'))
except Exception:
    pg.PAUSE=0.0

desktop=Desktop()
cursor=SystemCursor()
watch_cursor=WatchCursor()
windows_version=desktop.get_windows_version()
default_language=desktop.get_default_language()

# Vision detector (YOLO / YOLO-World); now preloaded at startup
vision_detector=None
# High-FPS frame stream (DXGI or fallback)
frame_stream=None
reflex_policy=None

instructions=dedent(f'''
Windows MCP server provides tools to interact directly with the {windows_version} desktop, 
thus enabling to operate the desktop on the user's behalf.
''')

@asynccontextmanager
async def lifespan(app: FastMCP):
    """Runs initialization code before the server starts and cleanup code after it shuts down."""
    try:
        watch_cursor.start()
        await asyncio.sleep(1) # Simulate startup latency
        # Preload vision model (standard YOLO by default; YOLO-World optional)
        try:
            from src.vision.world import VisionDetector as _VD
            world_only = os.getenv('WINDOWS_MCP_VISION_WORLD_ONLY','0').lower() in ['1','true','yes','on']
            model = os.getenv('WINDOWS_MCP_VISION_MODEL', None)
            global vision_detector
            vision_detector = _VD(model=model, world_only=world_only)
        except Exception:
            # Non-fatal: vision remains unavailable until tool call attempts
            pass
        # Optional: autostart frame stream via env
        auto=os.getenv('WINDOWS_MCP_FRAMESTREAM_AUTOSTART','0').lower() in ['1','true','yes','on']
        if auto:
            try:
                fps=int(os.getenv('WINDOWS_MCP_FRAMESTREAM_FPS','60'))
                downscale=float(os.getenv('WINDOWS_MCP_FRAMESTREAM_DOWNSCALE','1.0'))
                reg=os.getenv('WINDOWS_MCP_FRAMESTREAM_REGION','')
                region=None
                if reg:
                    parts=[int(p.strip()) for p in reg.split(',') if p.strip()]
                    if len(parts)==4:
                        region=parts
                frame_stream_start(fps=fps, region=region, downscale=downscale)
            except Exception as _:
                pass
        yield
    finally:
        watch_cursor.stop()
        try:
            if frame_stream is not None:
                frame_stream.stop()
        except Exception:
            pass

mcp=FastMCP(name='windows-mcp',instructions=instructions,lifespan=lifespan)

@mcp.tool(name="App-Tool", description="Manages Windows applications through launch, resize, and window switching operations.")
def app_tool(mode:Literal['launch','resize','switch'],name:str|None=None,window_loc:list[int]|None=None,window_size:list[int]|None=None):
    return desktop.app(mode,name,window_loc,window_size)
    
@mcp.tool(name='Powershell-Tool', description='Execute PowerShell commands and return the output with status code')
def powershell_tool(command: str) -> str:
    response,status_code=desktop.execute_command(command)
    return f'Response: {response}\nStatus Code: {status_code}'

@mcp.tool(name='State-Tool',description='Capture comprehensive desktop state including default language used by user interface, focused/opened applications, interactive UI elements (buttons, text fields, menus), informative content (text, labels, status), and scrollable areas. Optionally includes visual screenshot when use_vision=True. Essential for understanding current desktop context and available UI interactions.')
def state_tool(use_vision:bool=False):
    desktop_state=desktop.get_state(use_vision=use_vision,as_bytes=True)
    interactive_elements=desktop_state.tree_state.interactive_elements_to_string()
    informative_elements=desktop_state.tree_state.informative_elements_to_string()
    scrollable_elements=desktop_state.tree_state.scrollable_elements_to_string()
    apps=desktop_state.apps_to_string()
    active_app=desktop_state.active_app_to_string()
    return [dedent(f'''
    Default Language of User:
    {default_language} with encoding: {desktop.encoding}
                            
    Focused App:
    {active_app}

    Opened Apps:
    {apps}

    List of Interactive Elements:
    {interactive_elements or 'No interactive elements found.'}

    List of Informative Elements:
    {informative_elements or 'No informative elements found.'}

    List of Scrollable Elements:
    {scrollable_elements or 'No scrollable elements found.'}
    ''')]+([Image(data=desktop_state.screenshot,format='png')] if use_vision else [])

@mcp.tool(name='Click-Tool',description='Click on UI elements at specific coordinates. Supports left/right/middle mouse buttons and single/double/triple clicks. Use coordinates from State-Tool output.')
def click_tool(loc:list[int],button:Literal['left','right','middle']='left',clicks:int=1)->str:
    if len(loc) != 2:
        raise ValueError("Location must be a list of exactly 2 integers [x, y]")
    x,y=loc[0],loc[1]
    desktop.click(loc=loc,button=button,clicks=clicks)
    num_clicks={1:'Single',2:'Double',3:'Triple'}
    return f'{num_clicks.get(clicks)} {button} clicked at ({x},{y}).'

@mcp.tool(name='Type-Tool',description='Type text into input fields, text areas, or focused elements. Set clear=True to replace existing text, False to append. Click on target element coordinates first.')
def type_tool(loc:list[int],text:str,clear:bool=False,press_enter:bool=False)->str:
    if len(loc) != 2:
        raise ValueError("Location must be a list of exactly 2 integers [x, y]")
    x,y=loc[0],loc[1]
    desktop.type(loc=loc,text=text,clear=clear,press_enter=press_enter)
    return f'Typed {text} at ({x},{y}).'

@mcp.tool(name='Scroll-Tool',description='Scroll at specific coordinates or current mouse position. Use wheel_times to control scroll amount (1 wheel = ~3-5 lines). Essential for navigating lists, web pages, and long content.')
def scroll_tool(loc:list[int]=None,type:Literal['horizontal','vertical']='vertical',direction:Literal['up','down','left','right']='down',wheel_times:int=1)->str:
    if loc and len(loc) != 2:
        raise ValueError("Location must be a list of exactly 2 integers [x, y]")
    response=desktop.scroll(loc,type,direction,wheel_times)
    if response:
        return response
    return f'Scrolled {type} {direction} by {wheel_times} wheel times'+f' at ({loc[0]},{loc[1]}).' if loc else ''

@mcp.tool(name='Drag-Tool',description='Drag and drop operation from current coordinates to destination coordinates. Useful for moving files, resizing windows, or drag-and-drop interactions.')
def drag_tool(to_loc:list[int])->str:
    if len(to_loc) != 2:
        raise ValueError("to_loc must be a list of exactly 2 integers [x, y]")
    desktop.drag(to_loc)
    x2,y2=to_loc[0],to_loc[1]
    return f'Dragged the element to ({x2},{y2}).'

@mcp.tool(name='Move-Tool',description='Move mouse cursor to specific coordinates without clicking. Useful for hovering over elements or positioning cursor before other actions.')
def move_tool(to_loc:list[int])->str:
    if len(to_loc) != 2:
        raise ValueError("to_loc must be a list of exactly 2 integers [x, y]")
    x,y=to_loc[0],to_loc[1]
    desktop.move(to_loc)
    return f'Moved the mouse pointer to ({x},{y}).'


@mcp.tool(name='Input-Debug-Move', description='DEBUG: Move via backend directly and report OS cursor pos + virtual screen metrics.')
def input_debug_move(loc:list[int]):
    if len(loc) != 2:
        raise ValueError("loc must be [x,y]")
    x, y = int(loc[0]), int(loc[1])
    # Try direct backend move (bypass rate limiter)
    try:
        if desktop.input_backend:
            desktop.input_backend.move(x, y)
        else:
            pg.moveTo(x, y, duration=0.05)
    except Exception as e:
        pass
    # Read OS cursor (virtual desktop coordinates)
    class POINT(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
    pt = POINT()
    ok = ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    # Virtual screen metrics
    SM_XVIRTUALSCREEN = 76
    SM_YVIRTUALSCREEN = 77
    SM_CXVIRTUALSCREEN = 78
    SM_CYVIRTUALSCREEN = 79
    user32 = ctypes.windll.user32
    left = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
    top = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
    width = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
    height = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
    return (
        f"Requested move to ({x},{y})\n"
        f"OS cursor pos: ({pt.x},{pt.y}) ok={ok}\n"
        f"Virtual screen: left={left}, top={top}, width={width}, height={height}\n"
        f"Backend: {desktop.input_backend.info() if desktop.input_backend else 'None'}"
    )

@mcp.tool(name='Shortcut-Tool',description='Execute keyboard shortcuts using key combinations. Pass keys as list (e.g., ctrl+c for copy, alt+tab for app switching, win+r for Run dialog, win is for opening the start menu).')
def shortcut_tool(shortcut:str):
    desktop.shortcut(shortcut)
    return f"Pressed {shortcut}."

@mcp.tool(name='Wait-Tool',description='Pause execution for specified duration in seconds. Useful for waiting for applications to load, animations to complete, or adding delays between actions.')
def wait_tool(duration:int)->str:
    pg.sleep(duration)
    return f'Waited for {duration} seconds.'

@mcp.tool(name='Scrape-Tool',description='Fetch and convert webpage content to markdown format. Provide full URL including protocol (http/https). Returns structured text content suitable for analysis.')
def scrape_tool(url:str)->str:
    content=desktop.scrape(url)
    return f'Scraped the contents of the entire webpage:\n{content}'


@mcp.tool(name='Vision-Detect-Tool', description='Run YOLO detection on a desktop screenshot (standard by default; YOLO-World optional). Prompts should be object classes (e.g., person, bottle). Optional: model, imgsz and region=[l,t,r,b]. return_mode: attachment|data_uri|both; save=true to write PNG.')
def vision_detect_tool(prompts:list[str]|str|None=None, prompt:str|None=None, model:str|None=None, conf:float=0.25, iou:float=0.45, max_det:int=50, use_vision:bool=True, imgsz:int|None=None, region:list[int]|None=None, return_mode:Literal['attachment','data_uri','both']='attachment', save:bool=False, filename:str|None=None):
    global vision_detector
    try:
        from src.vision.world import VisionDetector as _VD
        # Capture screenshot at full scale for best accuracy
        screenshot=desktop.get_screenshot(scale=1.0)
        world_only = os.getenv('WINDOWS_MCP_VISION_WORLD_ONLY','0').lower() in ['1','true','yes','on']
        if vision_detector is None or model:
            # Re-init if first time or user requested a specific model
            vision_detector=_VD(model=model, world_only=world_only)
        # normalize prompts (accept list or single string via prompts/prompt)
        _prompts: list[str] | None = None
        if isinstance(prompts, str):
            s=prompts.strip()
            _prompts=[s] if s else None
        elif isinstance(prompts, list):
            _prompts=[str(x) for x in prompts]
        if prompt:
            s=prompt.strip()
            if s:
                _prompts = (_prompts or []) + [s]
        detections=vision_detector.detect(screenshot, prompts=_prompts, conf=conf, iou=iou, max_det=max_det, imgsz=imgsz, region=region if region and len(region)==4 else None)
        table=detections.to_table()
        count=len(detections.items)
        annotated=_VD.visualize(screenshot, detections)
        img_bytes=_VD.to_png_bytes(annotated)
        saved_path = None
        if save:
            try:
                from src.utils.paths import save_bytes
                saved_path = save_bytes(img_bytes, filename=filename, prefix='vision', ext='png')
            except Exception:
                saved_path = None
        header = dedent(f'''\
        Vision Backend: {vision_detector.backend.name} ({'loaded' if vision_detector.backend.loaded else 'not loaded'})\n\
        {vision_detector.backend.details}\n\
        Detections (count={count}):\n\
        {table}\n\
        {f"Saved: {saved_path}" if saved_path else ''}\n\
        ''')
        if not use_vision:
            return [table]
        if return_mode == 'attachment':
            return [header, Image(data=img_bytes, format='png')] if not saved_path else [header, saved_path]
        elif return_mode == 'data_uri':
            uri = 'data:image/png;base64,' + base64.b64encode(img_bytes).decode('utf-8')
            body = header + f"\nAnnotated Image (data URI):\n{uri}"
            return [body] if not saved_path else [body, saved_path]
        else:  # both
            uri = 'data:image/png;base64,' + base64.b64encode(img_bytes).decode('utf-8')
            return [header + f"\nAnnotated Image (data URI):\n{uri}", Image(data=img_bytes, format='png')] if not saved_path else [header + f"\nAnnotated Image (data URI):\n{uri}", saved_path]
    except Exception as ex:
        msg=str(ex)
        if 'No module named' in msg and 'clip' in msg:
            return (
                'Vision detection failed: CLIP module missing. '
                'Install with: "uv sync --extra vision_world" or '
                '"uv pip install \"git+https://github.com/ultralytics/CLIP.git#egg=clip\" ftfy regex tqdm".'
            )
        if 'module \'' in msg and 'regex' in msg and "has no attribute 'compile'" in msg:
            return (
                'Vision detection failed: regex wheel issue. '
                'Fix by reinstalling a compatible wheel: '
                '"uv pip uninstall -y regex" then '
                '"uv pip install --only-binary=:all: --upgrade regex". '
                'If wheels are unavailable for your Python version, try pre-releases: '
                '"uv pip install --pre --only-binary=:all: regex". '
                'Also ensure no local file named "regex.py" shadows the package.'
            )
        return f"Vision detection failed: {msg}"


 


@mcp.tool(name='Vision-Annotate-Tool', description='Store VLM/client-provided annotations for the active window. Each annotation is {label, bbox:[x1,y1,x2,y2], score?}.')
def vision_annotate_tool(annotations:list[dict], mode:Literal['append','set']='append')->str:
    handle=desktop.get_active_handle()
    if handle is None or desktop.vision_memory is None:
        return 'Vision memory not available.'
    from src.vision.memory import Annotation
    items=[Annotation(label=a.get('label','object'), bbox=a.get('bbox',[0,0,0,0]), score=a.get('score')) for a in annotations]
    if mode=='set':
        desktop.vision_memory.set(handle, items)
    else:
        desktop.vision_memory.append(handle, items)
    return f'Stored {len(items)} annotations for handle {handle}.'


@mcp.tool(name='Vision-Get-Annotations-Tool', description='Get stored annotations for the active window (from client/VLM or previous detections).')
def vision_get_annotations_tool():
    handle=desktop.get_active_handle()
    if handle is None or desktop.vision_memory is None:
        return 'Vision memory not available.'
    return desktop.vision_memory.to_serializable(handle)


@mcp.tool(name='Vision-Clear-Annotations-Tool', description='Clear stored annotations for the active window or all if clear_all=True.')
def vision_clear_annotations_tool(clear_all:bool=False)->str:
    if desktop.vision_memory is None:
        return 'Vision memory not available.'
    if clear_all:
        desktop.vision_memory.clear()
        return 'Cleared all annotations.'
    handle=desktop.get_active_handle()
    if handle is None:
        return 'No active window.'
    desktop.vision_memory.clear(handle)
    return f'Cleared annotations for handle {handle}.'


@mcp.tool(name='Frame-Stream-Start', description='Start a high-FPS capture stream using DXGI if available. region=[left,top,right,bottom], downscale in 0..1.')
def frame_stream_start(fps:int=60, region:list[int]|None=None, downscale:float=1.0, color:str='RGB'):
    global frame_stream
    try:
        if frame_stream is None:
            from src.sidecar.stream import FrameStream, CaptureConfig
            frame_stream=FrameStream()
        cfg_kwargs={
            'fps': fps,
            'downscale': downscale,
            'color': color
        }
        if region and len(region)==4:
            cfg_kwargs['region']=(region[0],region[1],region[2],region[3])
        from src.sidecar.stream import CaptureConfig
        frame_stream.start(CaptureConfig(**cfg_kwargs))
        return f'Started frame stream at {fps} FPS.'
    except Exception as ex:
        return f'Failed to start frame stream: {ex}'


@mcp.tool(name='Frame-Stream-Stop', description='Stop the high-FPS capture stream if running.')
def frame_stream_stop():
    global frame_stream
    if frame_stream is None:
        return 'No frame stream instance.'
    frame_stream.stop()
    return 'Stopped frame stream.'


@mcp.tool(name='Frame-Stream-Get', description='Get the latest captured frame from the stream. return_mode: attachment|data_uri; save to file with save=true.')
def frame_stream_get(use_vision:bool=True, return_mode:Literal['attachment','data_uri']='attachment', save:bool=False, filename:str|None=None):
    if frame_stream is None:
        return 'Frame stream not started.'
    img=frame_stream.get_latest()
    if img is None:
        return 'No frame available yet.'
    from src.vision.world import VisionDetector
    if not use_vision:
        if not save:
            return 'ok'
        from src.utils.paths import save_bytes
        saved = save_bytes(VisionDetector.to_png_bytes(img), filename=filename, prefix='frame', ext='png')
        return [saved]
    img_bytes=VisionDetector.to_png_bytes(img)
    saved_path=None
    if save:
        try:
            from src.utils.paths import save_bytes
            saved_path = save_bytes(img_bytes, filename=filename, prefix='frame', ext='png')
        except Exception:
            saved_path=None
    if return_mode=='attachment':
        return [Image(data=img_bytes, format='png')] if not saved_path else [saved_path]
    else:
        uri='data:image/png;base64,'+base64.b64encode(img_bytes).decode('utf-8')
        return [uri] if not saved_path else [uri, saved_path]

@mcp.tool(name='Output-Dir-Info', description='Return the directory path used for saving images. Override via WINDOWS_MCP_OUTPUT_DIR env var.')
def output_dir_info():
    try:
        from src.utils.paths import ensure_output_dir
        p = ensure_output_dir()
        return str(p)
    except Exception as ex:
        return f'Failed to get output directory: {ex}'


@mcp.tool(name='Reflex-Load', description='Load or reset the fast reflex policy. Provide module and object name, or leave empty for NoOp.')
def reflex_load(module:str|None=None, object:str|None=None)->str:
    global reflex_policy
    if not module or not object:
        from src.reflex.policy import NoOpPolicy
        reflex_policy=NoOpPolicy()
        return 'Loaded NoOp reflex policy.'
    try:
        from src.reflex.policy import load_policy
        reflex_policy=load_policy(module, object)
        return f'Loaded reflex policy {module}:{object}.'
    except Exception as ex:
        return f'Failed to load reflex policy: {ex}'


@mcp.tool(name='Reflex-Step', description='Run one reflex step on the latest frame and execute the resulting actions via rate-limited input.')
def reflex_step()->str:
    global reflex_policy
    if reflex_policy is None:
        from src.reflex.policy import NoOpPolicy
        reflex_policy=NoOpPolicy()
    # Prefer stream frame; fallback to screenshot
    img=None
    if frame_stream is not None:
        img=frame_stream.get_latest()
    if img is None:
        img=desktop.get_screenshot(scale=1.0)
    actions=reflex_policy.predict(img)
    # Execute
    executed=0
    for a in actions:
        try:
            if a.kind=='move' and a.x is not None and a.y is not None:
                desktop.move((a.x,a.y))
            elif a.kind=='click' and a.x is not None and a.y is not None:
                desktop.click((a.x,a.y), button=a.button, clicks=a.clicks)
            elif a.kind=='shortcut' and a.combo:
                desktop.shortcut(a.combo)
            executed+=1
        except Exception:
            pass
    return f'Reflex executed {executed} actions.'


@mcp.tool(name='Input-RateLimiter-Config', description='Configure per-game input rate limiting. Provide move_hz, max_delta, smooth in 0..1, clicks_per_sec, keys_per_sec.')
def input_rate_config(move_hz:float|None=None, max_delta:int|None=None, smooth:float|None=None, clicks_per_sec:float|None=None, keys_per_sec:float|None=None):
    try:
        from src.input.rate import RateConfig
        cfg=desktop.rate_limiter.cfg
        if move_hz is not None:
            cfg.mouse_move_hz=float(move_hz)
        if max_delta is not None:
            cfg.mouse_max_delta=int(max_delta)
        if smooth is not None:
            cfg.mouse_smooth=float(smooth)
        if clicks_per_sec is not None:
            cfg.clicks_per_sec=float(clicks_per_sec)
        if keys_per_sec is not None:
            cfg.keys_per_sec=float(keys_per_sec)
        desktop.rate_limiter.update_config(cfg)
        return f'Updated rate limits: {cfg}'
    except Exception as ex:
        return f'Failed to update rate limits: {ex}'


@mcp.tool(name='Input-HumanMove-Config', description='Enable or tune human-like cursor motion (single monitor only). Params: enabled=true/false, curve[0..1], jitter[0..1], min_dur, max_dur, and optional move_hz to adjust stepping speed.')
def input_humanmove_config(enabled:bool|None=None, curve:float|None=None, jitter:float|None=None, min_dur:float|None=None, max_dur:float|None=None, move_hz:float|None=None):
    # Update desktop human-move runtime flags
    if enabled is not None:
        desktop._human_move = bool(enabled)
    def _clip01(v: float|None, default: float) -> float:
        if v is None:
            return default
        try:
            return max(0.0, min(1.0, float(v)))
        except Exception:
            return default
    def _pos(v: float|None, default: float) -> float:
        if v is None:
            return default
        try:
            return max(0.0, float(v))
        except Exception:
            return default
    desktop._human_curve = _clip01(curve, desktop._human_curve)
    desktop._human_jitter = _clip01(jitter, desktop._human_jitter)
    desktop._human_min_dur = max(0.01, _pos(min_dur, desktop._human_min_dur))
    desktop._human_max_dur = max(desktop._human_min_dur, _pos(max_dur, desktop._human_max_dur))
    # Optionally adjust rate limiter move_hz for smoother stepping
    if move_hz is not None and desktop.rate_limiter:
        try:
            mhz = float(move_hz)
            desktop.rate_limiter.cfg.mouse_move_hz = max(15.0, min(480.0, mhz))
        except Exception:
            pass
    return (
        f"HumanMove enabled={desktop._human_move}, curve={desktop._human_curve}, jitter={desktop._human_jitter}, "
        f"min_dur={desktop._human_min_dur}, max_dur={desktop._human_max_dur}, move_hz={desktop.rate_limiter.cfg.mouse_move_hz if desktop.rate_limiter else 'n/a'}"
    )


@click.command()
@click.option(
    "--transport",
    help="The transport layer used by the MCP server.",
    type=click.Choice(['stdio','sse','streamable-http']),
    default='stdio'
)
@click.option(
    "--host",
    help="Host to bind the SSE/Streamable HTTP server.",
    default="localhost",
    type=str,
    show_default=True
)
@click.option(
    "--port",
    help="Port to bind the SSE/Streamable HTTP server.",
    default=8000,
    type=int,
    show_default=True
)
def main(transport, host, port):
    if transport=='stdio':
        mcp.run()
    else:
        mcp.run(transport=transport,host=host,port=port)

if __name__ == "__main__":
    main()
