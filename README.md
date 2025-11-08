[![MseeP.ai Security Assessment Badge](https://mseep.net/pr/cursortouch-windows-mcp-badge.png)](https://mseep.ai/app/cursortouch-windows-mcp)

<div align="center">
  <h1>🪟 Windows-MCP</h1>

  <a href="https://github.com/CursorTouch/Windows-MCP/blob/main/LICENSE">
    <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
  </a>
  <img src="https://img.shields.io/badge/python-3.13%2B-blue" alt="Python">
  <img src="https://img.shields.io/badge/platform-Windows%207–11-blue" alt="Platform: Windows 7 to 11">
  <img src="https://img.shields.io/github/last-commit/CursorTouch/Windows-MCP" alt="Last Commit">
  <br>
  <a href="https://x.com/CursorTouch">
    <img src="https://img.shields.io/badge/follow-%40CursorTouch-1DA1F2?logo=twitter&style=flat" alt="Follow on Twitter">
  </a>
  <a href="https://discord.com/invite/Aue9Yj2VzS">
    <img src="https://img.shields.io/badge/Join%20on-Discord-5865F2?logo=discord&logoColor=white&style=flat" alt="Join us on Discord">
  </a>

</div>

<br>

**Windows MCP** is a lightweight, open-source project that enables seamless integration between AI agents and the Windows operating system. Acting as an MCP server bridges the gap between LLMs and the Windows operating system, allowing agents to perform tasks such as **file navigation, application control, UI interaction, QA testing,** and more.

mcp-name: io.github.CursorTouch/Windows-MCP

## Updates

- Windows-MCP is added to [MCP Registry](https://github.com/modelcontextprotocol/registry)
- Try out 🪟[Windows-Use](https://github.com/CursorTouch/Windows-Use)!!, an agent built using Windows-MCP.
- Windows-MCP is now featured as Desktop Extension in `Claude Desktop`.

- New high‑FPS capture sidecar (DXGI first; fallbacks) with MCP tools: `Frame-Stream-Start`/`Stop`/`Get`.
- New SendInput‑first backend via IbInputSimulator (default `IbSendInit("AnyDriver")`), with SendInput/PyAutoGUI fallback.
- Per‑game input rate limiter; MCP tool: `Input-RateLimiter-Config`.
- Reflex layer scaffolding for Strategy A; MCP tools: `Reflex-Load`, `Reflex-Step`.

### Configuration (Environment Variables)
- `WINDOWS_MCP_INPUT_BACKEND` (default `ibsim`): `ibsim` or `pyautogui`.
- `WINDOWS_MCP_INPUT_DRIVER` (default `AnyDriver`): IbInputSimulator driver (e.g., `AnyDriver`, `Logitech`, `LogitechGHubNew`, `Razer`, `DD`, `MouClassInputInjection`).
- `WINDOWS_MCP_RATE_MOVE_HZ`/`_MAX_DELTA`/`_SMOOTH`/`_CPS`/`_KPS`: rate limits.
- `WINDOWS_MCP_FRAMESTREAM_AUTOSTART` (0/1), `WINDOWS_MCP_FRAMESTREAM_FPS`, `WINDOWS_MCP_FRAMESTREAM_DOWNSCALE`, `WINDOWS_MCP_FRAMESTREAM_REGION` (`l,t,r,b`).
- `WINDOWS_MCP_VISION_WORLD_ONLY` (1/0), `WINDOWS_MCP_VISION_MODEL`。
- `WINDOWS_MCP_VISION_IMGSZ` (default `640`): letterbox size for YOLO input。
- `WINDOWS_MCP_PG_FAILSAFE` (0/1), `WINDOWS_MCP_PG_PAUSE` (sec)。
- `WINDOWS_MCP_OUTPUT_DIR`: directory to save annotated images/frames (defaults to `%LOCALAPPDATA%/Windows-MCP/outputs`)。

Example (Codex/Claude Desktop env):
```json
{
  "WINDOWS_MCP_INPUT_BACKEND": "ibsim",
  "WINDOWS_MCP_INPUT_DRIVER": "AnyDriver",
  "WINDOWS_MCP_FRAMESTREAM_AUTOSTART": "1",
  "WINDOWS_MCP_FRAMESTREAM_FPS": "120",
  "WINDOWS_MCP_RATE_MOVE_HZ": "120",
  "WINDOWS_MCP_RATE_SMOOTH": "0.15"
}
```

### Vision Assistance (YOLO)

Optional computer‑vision tools detect on‑screen objects. Default backend is standard Ultralytics YOLO; YOLO‑World is supported when enabled.

- `Vision-Detect-Tool`: object detection on a desktop screenshot.
  - Backend: standard YOLO by default. Set `WINDOWS_MCP_VISION_WORLD_ONLY=1` to use YOLO‑World and accept open‑vocabulary `prompts`.
  - Optional params: `imgsz` (default 640), `region=[l,t,r,b]` for ROI。會自動 letterbox 並將方框映射回整個螢幕座標。
  - Output options: `return_mode=attachment|data_uri|both`, `save=true`, `filename="name.png"`（檔案會存到 `WINDOWS_MCP_OUTPUT_DIR`）。
- `Vision-Annotate-Tool`: store VLM/client annotations back to the server for the active window.
- `Vision-Get-Annotations-Tool` / `Vision-Clear-Annotations-Tool`.

Environment variables:
- `WINDOWS_MCP_VISION_WORLD_ONLY` (default `0`)
- `WINDOWS_MCP_VISION_MODEL` (default `yolov8n.pt` for standard YOLO; use a `*-world*.pt` to enable YOLO‑World)
- `WINDOWS_MCP_VISION_MODEL_STD` (default `yolov8n.pt`): model used when falling back from YOLO‑World to standard YOLO
- `WINDOWS_MCP_VISION_MODEL_DIRS`: `;`‑separated search paths for model files

Install (optional extras):

```bash
# Standard YOLO only
uv sync --extra vision

# YOLO‑World support (adds CLIP)
uv sync --extra vision_world

# High‑FPS capture only (DXGI + fallbacks)
uv sync --extra capture

# Everything
uv sync --extra full

# If extras are not available in your setup, install CLIP manually once:
# uv pip install "git+https://github.com/ultralytics/CLIP.git#egg=clip" ftfy regex tqdm
```

### Supported Operating Systems

- Windows 7
- Windows 8, 8.1
- Windows 10
- Windows 11  

## 🎥 Demos

<https://github.com/user-attachments/assets/d0e7ed1d-6189-4de6-838a-5ef8e1cad54e>

<https://github.com/user-attachments/assets/d2b372dc-8d00-4d71-9677-4c64f5987485>

## ✨ Key Features

- **Seamless Windows Integration**  
  Interacts natively with Windows UI elements, opens apps, controls windows, simulates user input, and more.

- **Use Any LLM (Vision Optional)**
   Unlike many automation tools, Windows MCP doesn't rely on any traditional computer vision techniques or specific fine-tuned models; it works with any LLMs, reducing complexity and setup time.

- **Rich Toolset for UI Automation**  
  Includes tools for basic keyboard, mouse operation and capturing window/UI state.

- **Lightweight & Open-Source**  
  Minimal dependencies and easy setup with full source code available under MIT license.

- **Customizable & Extendable**  
  Easily adapt or extend tools to suit your unique automation or AI integration needs.

- **Real-Time Interaction**  
  Typical latency between actions (e.g., from one mouse click to the next) ranges from **0.7 to 2.5 secs**, and may slightly vary based on the number of active applications and system load, also the inferencing speed of the llm.

## 🛠️Installation

### Prerequisites

- Python 3.13+
- UV (Package Manager) from Astra, install with `pip install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`
- `English` as the default language in Windows highly preferred or disable the `Launch-Tool` and `Switch-Tool` in the MCP Server for Windows with other languages.

<details>
  <summary>Install in Claude Desktop</summary>

  1. Install [Claude Desktop](https://claude.ai/download) and

```shell
npm install -g @anthropic-ai/mcpb
```

  2. Clone the repository.

```shell
git clone https://github.com/CursorTouch/Windows-MCP.git

cd Windows-MCP
```

  3. Build Desktop Extension `MCPB`:

```shell
npx @anthropic-ai/mcpb pack
```

  4. Open Claude Desktop:

Go to `Settings->Extensions->Advance Settings->Install Extension` (locate the `.mcpb` file)-> Install

  5. Enjoy 🥳.

For additional Claude Desktop integration troubleshooting, see the [MCP documentation](https://modelcontextprotocol.io/quickstart/server#claude-for-desktop-integration-issues). The documentation includes helpful tips for checking logs and resolving common issues.
</details>

<details>
  <summary>Install in Perplexity Desktop</summary>

  1. Install [Perplexity Desktop](https://apps.microsoft.com/detail/xp8jnqfbqh6pvf):

  2. Clone the repository.

```shell
git clone https://github.com/CursorTouch/Windows-MCP.git

cd Windows-MCP
```
  
  3. Open Perplexity Desktop:

Go to `Settings->Connectors->Add Connector->Advanced`

  4. Enter the name as `Windows-MCP`, then paste the following JSON in the text area.

```json
{
  "command": "uv",
  "args": [
    "--directory",
    "<path to the windows-mcp directory>",
    "run",
    "main.py"
  ],
  "env": {
    "WINDOWS_MCP_INPUT_BACKEND": "ibsim",
    "WINDOWS_MCP_INPUT_DRIVER": "AnyDriver",
    "WINDOWS_MCP_FRAMESTREAM_AUTOSTART": "1",
    "WINDOWS_MCP_FRAMESTREAM_FPS": "120",
    "WINDOWS_MCP_RATE_MOVE_HZ": "120",
    "WINDOWS_MCP_RATE_SMOOTH": "0.15"
  }
}
```

5. Click `Save` and Enjoy 🥳.

For additional Claude Desktop integration troubleshooting, see the [Perplexity MCP Support](https://www.perplexity.ai/help-center/en/articles/11502712-local-and-remote-mcps-for-perplexity). The documentation includes helpful tips for checking logs and resolving common issues.
</details>

<details>
  <summary> Install in Gemini CLI</summary>

  1. Install Gemini CLI:

```shell
npm install -g @google/gemini-cli
```

  2. Clone the repository.

```shell
git clone https://github.com/CursorTouch/Windows-MCP.git

cd Windows-MCP
```

  3. Navigate to `%USERPROFILE%/.gemini` in File Explorer and open `settings.json`.

  4. Add the `windows-mcp` config in the `settings.json` and save it.

```json
{
  "theme": "Default",
  ...
//MCP Server Config
  "mcpServers": {
    "windows-mcp": {
      "command": "uv",
      "args": [
        "--directory",
        "<path to the windows-mcp directory>",
        "run",
        "main.py"
      ],
      "env": {
        "WINDOWS_MCP_INPUT_BACKEND": "ibsim",
        "WINDOWS_MCP_INPUT_DRIVER": "AnyDriver",
        "WINDOWS_MCP_FRAMESTREAM_AUTOSTART": "1",
        "WINDOWS_MCP_FRAMESTREAM_FPS": "120",
        "WINDOWS_MCP_RATE_MOVE_HZ": "120",
        "WINDOWS_MCP_RATE_SMOOTH": "0.15"
      }
    }
  }
}
```

  5. Rerun Gemini CLI in terminal. Enjoy 🥳
</details>

<details>
  <summary>Install in Qwen Code</summary>
  1. Install Qwen Code:

```shell
npm install -g @qwen-code/qwen-code@latest
```
  2. Clone the repository.

```shell
git clone https://github.com/CursorTouch/Windows-MCP.git

cd Windows-MCP
```

  3. Navigate to `%USERPROFILE%/.qwen/settings.json`.

  4. Add the `windows-mcp` config in the `settings.json` and save it.

```json
{
//MCP Server Config
  "mcpServers": {
    "windows-mcp": {
      "command": "uv",
      "args": [
        "--directory",
        "<path to the windows-mcp directory>",
        "run",
        "main.py"
      ],
      "env": {
        "WINDOWS_MCP_INPUT_BACKEND": "ibsim",
        "WINDOWS_MCP_INPUT_DRIVER": "AnyDriver",
        "WINDOWS_MCP_FRAMESTREAM_AUTOSTART": "1",
        "WINDOWS_MCP_FRAMESTREAM_FPS": "120",
        "WINDOWS_MCP_RATE_MOVE_HZ": "120",
        "WINDOWS_MCP_RATE_SMOOTH": "0.15"
      }
    }
  }
}
```

  5. Rerun Qwen Code in terminal. Enjoy 🥳
</details>

<details>
  <summary>Install in Codex CLI</summary>
  1. Install Codex CLI:

```shell
npm install -g @openai/codex
```
  2. Clone the repository.

```shell
git clone https://github.com/CursorTouch/Windows-MCP.git

cd Windows-MCP
```
  3. Navigate to `%USERPROFILE%/.codex/config.toml`.

  4. Add the `windows-mcp` config in the `config.toml` and save it.

```toml
[mcp_servers.windows-mcp]
command="uv"
args=[
  "--directory",
  "<path to the windows-mcp directory>",
  "run",
  "main.py"
]
env={
  WINDOWS_MCP_INPUT_BACKEND="ibsim",
  WINDOWS_MCP_INPUT_DRIVER="AnyDriver",
  WINDOWS_MCP_FRAMESTREAM_AUTOSTART="1",
  WINDOWS_MCP_FRAMESTREAM_FPS="120",
  WINDOWS_MCP_RATE_MOVE_HZ="120",
  WINDOWS_MCP_RATE_SMOOTH="0.15"
}
```

  5. Rerun Codex CLI in terminal. Enjoy 🥳
</details>

---

## 🔨MCP Tools

MCP Client can access the following tools to interact with Windows:

- `Click-Tool`: Click on the screen at the given coordinates.
- `Type-Tool`: Type text on an element (optionally clears existing text).
- `Clipboard-Tool`: Copy or paste using the system clipboard.
- `Scroll-Tool`: Scroll vertically or horizontally on the window or specific regions.
- `Drag-Tool`: Drag from one point to another.
- `Move-Tool`: Move mouse pointer.
- `Shortcut-Tool`: Press keyboard shortcuts (`Ctrl+c`, `Alt+Tab`, etc).
- `Key-Tool`: Press a single key.
- `Wait-Tool`: Pause for a defined duration.
- `State-Tool`: Combined snapshot of default language, browser, active apps and interactive, textual and scrollable elements along with screenshot of the desktop.
- `Resize-Tool`: Used to change the window size or location of an app.
- `Launch-Tool`: To launch an application from the start menu.
- `Shell-Tool`: To execute PowerShell commands.
- `Scrape-Tool`: To scrape the entire webpage for information.

## 🤝 Connect with Us
Stay updated and join our community:

- 📢 Follow us on [X](https://x.com/CursorTouch) for the latest news and updates

- 💬 Join our [Discord Community](https://discord.com/invite/Aue9Yj2VzS)

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=CursorTouch/Windows-MCP&type=Date)](https://www.star-history.com/#CursorTouch/Windows-MCP&Date)

## ⚠️Caution

This MCP interacts directly with your Windows operating system to perform actions. Use with caution and avoid deploying it in environments where such risks cannot be tolerated.

## 📝 Limitations

- Selecting specific sections of the text in a paragraph, as the MCP is relying on a11y tree. (⌛ Working on it.)
- `Type-Tool` is meant for typing text, not programming in IDE because of it types program as a whole in a file. (⌛ Working on it.)
- This MCP server can't be used to play video games.

## 🪪License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgements

Windows-MCP makes use of several excellent open-source projects that power its Windows automation features:

- [UIAutomation](https://github.com/yinkaisheng/Python-UIAutomation-for-Windows)

- [PyAutoGUI](https://github.com/asweigart/pyautogui)

Huge thanks to the maintainers and contributors of these libraries for their outstanding work and open-source spirit.

## 🤝Contributing

Contributions are welcome! Please see [CONTRIBUTING](CONTRIBUTING) for setup instructions and development guidelines.

Made with ❤️ by [CursorTouch](https://github.com/CursorTouch)

## Citation

```bibtex
@software{
  author       = {CursorTouch},
  title        = {Windows-MCP: Lightweight open-source project for integrating LLM agents with Windows},
  year         = {2024},
  publisher    = {GitHub},
  url={https://github.com/CursorTouch/Windows-MCP}
}
```
