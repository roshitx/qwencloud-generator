# QwenCloud Account Auto-Register + API Key Harvester

Automatically registers QwenCloud (Alibaba Bailian) accounts using Gmail dot-variants, harvests API keys via browser automation with proxy rotation.

## Features

- **Auto Register**: Signup → email verify → OTP → dashboard → API key extraction
- **Auto Resume**: Login existing accounts → API key extraction
- **Multi-threaded**: Run N browsers concurrently (`-t N`)
- **Xvfb mode**: Headed browser on virtual display (invisible, CF-safe)
- **TUI Dashboard**: Real-time worker status, progress bar, ETA, CPU/Mem
- **Proxy rotation**: Each account gets unique proxy
- **Gmail OAuth**: Multi-account Gmail token management
- **Censor mode**: Mask emails and API keys in output (`-c`)

## Prerequisites

1. **Python 3.11+**
2. **Google Chrome** (not Chromium)
3. **Xvfb**: `sudo apt install xvfb`
4. **Playwright**: `pip install -r requirements.txt && playwright install chromium`

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Add your proxies
Edit `proxy.txt` — one proxy per line:
```
username:password@host:port
```

### 3. Generate email list
```bash
python3 generate_email_list.py yourgmailuser -o email_list.txt
```

### 4. Set up Gmail OAuth
1. Create a project at https://console.cloud.google.com/
2. Enable Gmail API
3. Create OAuth 2.0 credentials (Desktop app)
4. Download `client_secret.json` to this folder
5. Update `gmail_auth.py` with your `client_id` and `client_secret` (or use client_secret.json)
6. Authorize each base Gmail account:
```bash
python3 gmail_auth.py
```

## Usage

### Register new accounts
```bash
# Single thread, browser visible
python3 run.py 10

# 5 threads, invisible (Xvfb)
python3 run.py 100 --headless -t 5

# 10 threads with censored output
python3 run.py 400 --headless -t 10 -c
```

### Resume existing accounts
```bash
python3 run.py 50 --headless -t 5 --resume
```

### Flags
| Flag | Description |
|---|---|
| `N` | Target number of successful API keys |
| `--headless` | Run via Xvfb (invisible browser) |
| `--resume` | Resume already-registered accounts via login |
| `-t N` | Number of concurrent threads |
| `-c` | Censor emails/API keys in output |
| `--log` | Show full subprocess logs |

## Files

| File | Purpose |
|---|---|
| `run.py` | Main entry point — orchestrator with threading + TUI |
| `qwencloud_full.py` | Browser automation — signup, login, API key extraction |
| `gmail_auth.py` | Gmail OAuth multi-account token management |
| `generate_email_list.py` | Generate Gmail dot-variants |
| `logger.py` | Colored logging utilities |
| `tui.py` | Terminal UI dashboard |
| `run_hidden.sh` | Xvfb wrapper script |
| `proxy.txt` | Your proxy list |
| `email_list.txt` | Gmail variants to register |
| `UI_MAP.md` | UI element reference for QwenCloud |

## How It Works

1. Each thread claims a unique email + proxy
2. Spawns `qwencloud_full.py` as subprocess (Playwright is not thread-safe)
3. Monitors subprocess output for progress updates
4. Parses `__RESULT__` JSON from stdout
5. Saves API keys to `api_keys.txt` and account data to `accounts.json`

## Notes

- Each browser instance gets 1 unique proxy — no reuse
- Gmail dot-variants work as separate QwenCloud accounts
- Stuck processes are killed after 30s of no output
- Total timeout per account: 300s
