# Turbo.az MCP Server

Turbo.az avtomobil bazarı üçün MCP (Model Context Protocol) server. Bu server Claude Desktop-a turbo.az-dan avtomobil axtarmaq və elan məlumatlarını əldə etmək imkanı verir.

## ⚠️ Vacib Qeyd

Turbo.az xaricdən (Azərbaycandan kənar) girişi bloklayır. Bu server **Azərbaycan IP-dən işləməlidir**:
- Lokal kompüterdə (Azərbaycanda)
- VPN vasitəsilə Azərbaycan IP ilə
- Azərbaycanda yerləşən VPS-dən

## 🚀 Quraşdırma

### 1. Tələblər

- Python 3.10+
- Google Chrome browser
- pip

### 2. Server quraşdırması

```bash
# Repo-nu klonla və ya faylları kopyala
cd turbo-az-mcp

# Virtual environment yarat
python -m venv venv

# Aktivləşdir
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Paketləri quraşdır
pip install -e .
```

### 3. Test et

```bash
# Serveri manual işə sal
python -m src.server
```

### 4. MCP-ni LLM olmadan test et

Serveri spawn edib tool çağırır (Chrome lazımdır):

```bash
uv run python scripts/test_mcp.py
```

## 🔧 Claude Desktop (local MCP, stdio)

**Local-only:** Claude Desktop runs the server as a subprocess. Do **not** use "Add custom connector" / Remote MCP URL.

1. Config faylını tap və aç:
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
   - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Linux**: `~/.config/Claude/claude_desktop_config.json`

2. `mcpServers` bölməsinə əlavə et (və ya layihədəki `claude_desktop_config.example.json`-u kopyala və `cwd`-i öz yoluna dəyiş):

**uv ilə (tövsiyə olunur):**
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

**Python / venv ilə:**
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

**Qeyd:** `cwd` layihə qovluğunun tam yoludur. Claude Desktop-u yenidən başladın.

### Claude Windows, server WSL-də

Claude Desktop Windows-da, layihə isə WSL-dədirsə, config-də `wsl` istifadə et. WSL non-interactive shell-də `uv` PATH-da olmaya bilər, ona görə venv python istifadə et:

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

`/home/javid/dev/turbo-mcp` əvəzinə öz WSL layihə yolunu yaz. Əgər venv `.venv` deyil (məs. `venv`), `.venv/bin/python` əvəzinə `venv/bin/python` yaz.

**WSL-də Chrome:** Server WSL-də işləyəndə Selenium üçün Chrome/Chromium WSL-də quraşdırılmalıdır (Windows Chrome işləməz). WSL terminalda:
```bash
sudo apt update && sudo apt install -y chromium-browser
```
Əgər `chromium-browser` snap tələb edirsə, Google Chrome for Linux quraşdırın və ya `CHROME_BINARY=/usr/bin/chromium` (və ya quraşdırılan yol) təyin edin.

## 📋 Mövcud Toollar

### 1. `search_cars`
Avtomobil axtarışı.

**Parametrlər:**
- `make` - Marka (BMW, Mercedes, Toyota və s.)
- `model` - Model (X5, E-Class və s.)
- `price_min` / `price_max` - Qiymət aralığı (AZN)
- `year_min` / `year_max` - İl aralığı
- `fuel_type` - Yanacaq: benzin, dizel, qaz, elektrik, hibrid
- `transmission` - avtomat, mexaniki
- `limit` - Nəticə sayı (default: 10)

**Nümunə sorğu:** "Turbo.az-da 2020-ci ildən yeni BMW X5 axtar, qiyməti 50000 AZN-ə qədər"

### 2. `get_car_details`
Elanın ətraflı məlumatları.

**Parametrlər:**
- `listing_id` - Elan ID-si və ya tam URL

**Nümunə sorğu:** "Turbo.az-da bu elanın detallarını göstər: 12345678"

### 3. `get_makes_models`
Marka və model siyahısı.

**Parametrlər:**
- `make` - Marka (modellərini görmək üçün, boş = bütün markalar)

**Nümunə sorğu:** "BMW-nin hansı modelləri var turbo.az-da?"

### 4. `get_trending`
Yeni/populyar elanlar.

**Parametrlər:**
- `category` - new, popular, vip
- `limit` - Nəticə sayı

## 🐛 Problemlər

### "403 Forbidden" xətası
- Azərbaycan IP-dən işlədiyindən əmin ol
- VPN istifadə et (Azərbaycan IP)

### ChromeDriver xətası
- Chrome brauzerin quraşdırıldığından əmin ol
- `webdriver-manager` avtomatik ChromeDriver yükləyir

### "DevToolsActivePort file doesn't exist" (WSL)
- `chromium-browser` (snap) WSL-də tez-tez işləmir. Google Chrome quraşdırın:
  ```bash
  wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
  sudo dpkg -i google-chrome-stable_current_amd64.deb
  sudo apt install -f
  ```
- Və ya virtual display ilə: `sudo apt install xvfb` sonra `xvfb-run -a uv run python scripts/test_mcp.py`

### Timeout xətası
- İnternet bağlantını yoxla
- turbo.az-ın işlədiyini yoxla

## 📄 Lisenziya

MIT
