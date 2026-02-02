# Turbo.az MCP Server

MCP (Model Context Protocol) server for Turbo.az automotive marketplace. This server enables Claude Desktop to search for cars and retrieve listing information from turbo.az.

## ⚠️ Important Note

Turbo.az blocks access from outside Azerbaijan. This server **must run from an Azerbaijani IP**:
- Local computer (in Azerbaijan)
- Via VPN with Azerbaijan IP
- From a VPS located in Azerbaijan

## 🚀 Installation

### 1. Requirements

- Python 3.10+
- Google Chrome browser
- pip

### 2. Server Setup

```bash
# Clone the repo or copy files
cd turbo-az-mcp

# Create virtual environment
python -m venv venv

# Activate
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install packages
pip install -e .
```

### 3. Test

```bash
# Run server manually
python -m src.server
```

### 4. Test MCP without LLM

Spawns the server and calls tools (requires Chrome):

```bash
uv run python scripts/test_mcp.py
```

## 🔧 Claude Desktop (local MCP, stdio)

**Local-only:** Claude Desktop runs the server as a subprocess. Do **not** use "Add custom connector" / Remote MCP URL.

1. Find and open the config file:
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
   - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Linux**: `~/.config/Claude/claude_desktop_config.json`

2. Add to `mcpServers` section (or copy `claude_desktop_config.example.json` from the project and change `cwd` to your path):

**With uv (recommended):**
```json
{
  "mcpServers": {
    "turbo-az": {
      "command": "uv",
      "args": ["run", "python", "-m", "src.server"],
      "cwd": "/home/javid/dev/turbo-mcp"
    }
  }
}
```

**With Python / venv:**
```json
{
  "mcpServers": {
    "turbo-az": {
      "command": "python",
      "args": ["-m", "src.server"],
      "cwd": "/home/javid/dev/turbo-mcp"
    }
  }
}
```

**Note:** `cwd` is the full path to the project folder. Restart Claude Desktop.

### Claude on Windows, Server in WSL

If Claude Desktop is on Windows but the project is in WSL, use `wsl` in config. WSL non-interactive shell may not have `uv` in PATH, so use venv python:

```json
{
  "mcpServers": {
    "turbo-az": {
      "command": "wsl",
      "args": ["bash", "-c", "cd /home/javid/dev/turbo-mcp && .venv/bin/python -m src.server"]
    }
  }
}
```

Replace `/home/javid/dev/turbo-mcp` with your WSL project path. If venv is not `.venv` (e.g. `venv`), use `venv/bin/python` instead of `.venv/bin/python`.

**Chrome in WSL:** When server runs in WSL, Chrome/Chromium must be installed in WSL for Selenium (Windows Chrome won't work). In WSL terminal:
```bash
sudo apt update && sudo apt install -y chromium-browser
```
If `chromium-browser` requires snap, install Google Chrome for Linux or set `CHROME_BINARY=/usr/bin/chromium` (or installed path).

## 📋 Available Tools

### 1. `search_cars`
Search for cars.

**Parameters:**
- `make` - Brand (BMW, Mercedes, Toyota, etc.)
- `model` - Model (X5, E-Class, etc.)
- `price_min` / `price_max` - Price range (AZN)
- `year_min` / `year_max` - Year range
- `fuel_type` - Fuel: benzin, dizel, qaz, elektrik, hibrid
- `transmission` - avtomat, mexaniki
- `limit` - Number of results (default: 10)

**Example query:** "Search for BMW X5 from 2020, price up to 50000 AZN on Turbo.az"

### 2. `get_car_details`
Detailed listing information.

**Parameters:**
- `listing_id` - Listing ID or full URL

**Example query:** "Show details of this listing on Turbo.az: 12345678"

### 3. `get_makes_models`
List of makes and models.

**Parameters:**
- `make` - Brand (to see its models, empty = all makes)

**Example query:** "What BMW models are available on turbo.az?"

### 4. `get_trending`
New/popular listings.

**Parameters:**
- `category` - new, popular, vip
- `limit` - Number of results

## 🐛 Troubleshooting

### "403 Forbidden" error
- Make sure you're running from Azerbaijan IP
- Use VPN (Azerbaijan IP)

### ChromeDriver error
- Make sure Chrome browser is installed
- `webdriver-manager` automatically downloads ChromeDriver

### "DevToolsActivePort file doesn't exist" (WSL)
- `chromium-browser` (snap) often doesn't work in WSL. Install Google Chrome:
  ```bash
  wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
  sudo dpkg -i google-chrome-stable_current_amd64.deb
  sudo apt install -f
  ```
- Or with virtual display: `sudo apt install xvfb` then `xvfb-run -a uv run python scripts/test_mcp.py`

### Timeout error
- Check internet connection
- Check if turbo.az is working

## 📄 License

MIT
