# Schwab-to-Discord - Complete Setup Guide

## Fresh Windows 11 Installation Guide

This guide walks you through setting up the Schwab-to-Discord trade notification bot on a completely fresh Windows 11 machine. Follow every step exactly.

---

## Table of Contents
1. [Overview](#overview)
2. [Prerequisites Checklist](#prerequisites-checklist)
3. [Part 0: Windows System Prerequisites](#part-0-windows-system-prerequisites) **(DO THIS FIRST!)**
4. [Part 1: Install Docker Desktop](#part-1-install-docker-desktop)
5. [Part 2: Install Git (Optional)](#part-2-install-git-optional)
6. [Part 3: Get the Project Files](#part-3-get-the-project-files)
7. [Part 4: Create Schwab Developer App](#part-4-create-schwab-developer-app)
8. [Part 5: Create Discord Webhook](#part-5-create-discord-webhook)
9. [Part 6: Configure the Bot](#part-6-configure-the-bot)
10. [Part 7: First-Time Schwab Authentication](#part-7-first-time-schwab-authentication)
11. [Part 8: Build and Run](#part-8-build-and-run)
12. [Part 9: Verify It's Working](#part-9-verify-its-working)
13. [Part 10: Optional - Google Sheets Export](#part-10-optional-google-sheets-export)
14. [Troubleshooting](#troubleshooting)
15. [Alternative Methods](#alternative-methods)
16. [Quick Reference](#quick-reference)

---

## Overview

**What is this?** A bot that monitors your Schwab brokerage account for filled trades and instantly posts notifications to Discord with gain/loss calculations.

**What it does:**
- Polls Schwab every 5 seconds for new filled orders
- Calculates cost basis and gain % using LIFO method
- Posts formatted notifications to Discord
- Exports trade history to Excel and Google Sheets (optional)

**What you need:**
- Windows 11 PC with internet
- ~20 minutes for setup
- Schwab brokerage account
- Discord server with webhook

---

## Prerequisites Checklist

| Item | Required? | How to Get It |
|------|-----------|---------------|
| Windows 11 | Yes | Already have it |
| Docker Desktop | Yes | Part 1 below |
| Git | Optional | Part 2 below |
| Schwab Brokerage Account | Yes | Already have it |
| Schwab Developer Account | Yes | Part 4 below |
| Discord Server | Yes | Part 5 below |
| Google Cloud Account | Optional | Part 10 below |

---

## Part 0: Windows System Prerequisites

**IMPORTANT: Complete this section BEFORE installing Docker!**

These are Windows system components that Docker and the bot depend on. On a fresh Windows 11 machine, some of these may not be installed.

### 0.1: Install WSL 2 (Windows Subsystem for Linux)

Docker Desktop requires WSL 2 to run Linux containers on Windows. **This is mandatory.**

**Step 0.1.1:** Open PowerShell **as Administrator**
- Right-click the Start button
- Click "Terminal (Admin)" or "Windows PowerShell (Admin)"
- Click "Yes" on the UAC prompt

**Step 0.1.2:** Run the WSL install command:
```powershell
wsl --install
```

**Expected output:**
```
Installing: Virtual Machine Platform
Installing: Windows Subsystem for Linux
Installing: Ubuntu
The requested operation is successful. Changes will not be effective until the system is rebooted.
```

**Step 0.1.3:** Restart your computer
```powershell
shutdown /r /t 0
```

**Step 0.1.4:** After restart, Ubuntu will auto-launch and ask you to create a username and password. Complete this setup.

**Step 0.1.5:** Verify WSL is installed:
```powershell
wsl --version
```

**Expected output:**
```
WSL version: 2.0.x
Kernel version: 5.15.x
...
```

### Verify WSL 2 is Default

```powershell
wsl --status
```

**Should show:**
```
Default Distribution: Ubuntu
Default Version: 2
```

**If it shows Version: 1, run:**
```powershell
wsl --set-default-version 2
```

---

### 0.2: Install Git for Windows (Includes Git Bash)

Git for Windows includes **Git Bash**, which provides a bash shell on Windows. Some commands and scripts require bash.

**Step 0.2.1:** Download Git for Windows:
```
https://git-scm.com/download/win
```

**Step 0.2.2:** Click "64-bit Git for Windows Setup"

**Step 0.2.3:** Run the installer

**Step 0.2.4:** Important installer options:
- **Select Components:** Keep defaults, ensure "Git Bash Here" is checked
- **Default editor:** Choose your preference (Notepad++ or VS Code recommended)
- **PATH environment:** Select "Git from the command line and also from 3rd-party software"
- **Line ending conversions:** Select "Checkout as-is, commit Unix-style line endings"
- **Terminal emulator:** Select "Use MinTTY (the default terminal of MSYS2)"

**Step 0.2.5:** Complete installation

### Verify Git Bash Installation

**Close and reopen PowerShell**, then run:
```powershell
git --version
```

**Expected output:**
```
git version 2.43.0.windows.1
```

**Also verify bash is available:**
```powershell
bash --version
```

**Expected output:**
```
GNU bash, version 5.2.x(1)-release ...
```

---

### 0.3: Install Windows Terminal (Optional but Recommended)

Windows Terminal is a modern terminal app that can run PowerShell, Git Bash, and WSL in tabs.

**Step 0.3.1:** Open Microsoft Store (search "Microsoft Store" in Start menu)

**Step 0.3.2:** Search for "Windows Terminal"

**Step 0.3.3:** Click "Get" or "Install"

---

### 0.4: Verify All Prerequisites

Run these commands in PowerShell to verify everything is installed:

```powershell
# Check WSL
wsl --version

# Check Git
git --version

# Check Bash (via Git)
bash --version
```

**All three should return version information, not errors.**

### If Any Check Fails

| Check | Error | Solution |
|-------|-------|----------|
| `wsl --version` | "not recognized" | Re-run `wsl --install` as Admin, restart |
| `git --version` | "not recognized" | Re-install Git for Windows, restart PowerShell |
| `bash --version` | "not recognized" | Re-install Git for Windows with Git Bash option |

---

## Part 1: Install Docker Desktop

Docker runs the bot in a container. This is required.

### Method A: Download from Website (Recommended)

**Step 1.1:** Open your web browser and go to:
```
https://www.docker.com/products/docker-desktop/
```

**Step 1.2:** Click the big blue "Download for Windows" button

**Step 1.3:** Wait for the download to complete (~500MB)

**Step 1.4:** Double-click the downloaded file: `Docker Desktop Installer.exe`

**Step 1.5:** When asked, make sure these options are CHECKED:
- [x] Use WSL 2 instead of Hyper-V (recommended)
- [x] Add shortcut to desktop

**Step 1.6:** Click "Ok" and wait for installation (5-10 minutes)

**Step 1.7:** Click "Close and restart" when prompted

**Step 1.8:** After restart, Docker Desktop should start automatically

**Step 1.9:** Accept the license agreement

### Verify Docker Installation

**Open PowerShell** (right-click Start button > "Terminal" or "PowerShell")

```powershell
docker --version
```

**Expected output:**
```
Docker version 24.0.7, build afdd53b
```

```powershell
docker compose version
```

**Expected output:**
```
Docker Compose version v2.23.0-desktop.1
```

### If Docker Won't Start - WSL 2 Setup

**Open PowerShell as Administrator:**
```powershell
wsl --install
```

**Restart your computer, then try Docker again.**

---

## Part 2: Install Git (Optional)

Only needed if cloning from a repository. Skip if copying files manually.

**Step 2.1:** Go to: `https://git-scm.com/download/win`

**Step 2.2:** Download and run the 64-bit installer

**Step 2.3:** Click "Next" through all screens (defaults are fine)

**Verify:**
```powershell
git --version
```

---

## Part 3: Get the Project Files

### Method A: Copy from Another Computer

**Step 3.1:** On your working computer, copy the entire folder:
```
C:\Users\Depache\stockbot-docker\schwab-to-discord
```

**Step 3.2:** Transfer to new computer using USB, network share, or cloud storage

**Step 3.3:** Place in your user folder:
```
C:\Users\YourUsername\stockbot-docker\schwab-to-discord
```

### Method B: Clone from Repository (If Available)

```powershell
cd C:\Users\YourUsername
git clone https://github.com/YOUR-REPO/stockbot-docker.git
cd stockbot-docker\schwab-to-discord
```

### Verify Files are Present

```powershell
cd C:\Users\YourUsername\stockbot-docker\schwab-to-discord
dir
```

**You should see:**
```
config/
data/
docs/
src/
tests/
docker-compose.yml
Dockerfile
main.py
pyproject.toml
README.md
```

---

## Part 4: Create Schwab Developer App

This is the most important step. You need to create a Schwab Developer account and register an app to get API credentials.

### Step 4.1: Create Schwab Developer Account

**Go to:**
```
https://developer.schwab.com/
```

**Click "Register" or "Sign Up"**

**Fill in your information:**
- Use the same email as your Schwab brokerage account (recommended)
- Create a password
- Verify your email

### Step 4.2: Create a New App

**After logging in, click "My Apps" or "Dashboard"**

**Click "Create App" or "Add App"**

**Fill in the form:**

| Field | Value |
|-------|-------|
| App Name | `schwab-to-discord` (or any name) |
| Description | `Trade notification bot` |
| Callback URL | `https://127.0.0.1` |

**IMPORTANT:** The Callback URL MUST be exactly `https://127.0.0.1` (with https, not http)

### Step 4.3: Wait for App Approval

- Schwab reviews all apps manually
- This can take 1-3 business days
- You'll get an email when approved
- Status changes from "Pending" to "Approved"

### Step 4.4: Get Your API Credentials

**Once approved, go to your app in the dashboard**

**You'll see:**
- **App Key** (also called Client ID): `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
- **App Secret** (also called Client Secret): `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

**Copy and save both values - you'll need them in Part 6**

### Verify App is Ready

- Status should say "Approved" or "Ready"
- Callback URL should show `https://127.0.0.1`
- Both App Key and App Secret should be visible

---

## Part 5: Create Discord Webhook

### Step 5.1: Open Discord

**Go to the server where you want trade notifications**

### Step 5.2: Create Webhook

**Right-click on the channel > "Edit Channel"**

**Click "Integrations" in the left sidebar**

**Click "Webhooks"**

**Click "New Webhook"**

**Configure:**
- Name: `Schwab Trades` (or any name)
- Avatar: Optional

**Click "Copy Webhook URL"**

**Save this URL - it looks like:**
```
https://discord.com/api/webhooks/1234567890/abcdefghijklmnop...
```

### Optional: Create Second Webhook

If you want trade alerts in two channels:
1. Go to the second channel
2. Create another webhook
3. Copy that URL too (for `DISCORD_WEBHOOK_2`)

### Optional: Get Role ID for Mentions

If you want the bot to @mention a role when trades happen:

1. Go to Server Settings > Roles
2. Find or create the role you want mentioned
3. Right-click the role > "Copy Role ID"
   - (If you don't see this, enable Developer Mode in User Settings > App Settings > Advanced)
4. Save the Role ID (a long number like `1234567890123456789`)

---

## Part 6: Configure the Bot

### Step 6.1: Create the Secrets File

**Navigate to the config folder:**
```powershell
cd C:\Users\YourUsername\stockbot-docker\schwab-to-discord\config
```

**Create the secrets file:**
```powershell
notepad .env.secrets
```

**Paste this template and fill in your values:**
```ini
# ===========================================
# SCHWAB API CREDENTIALS (REQUIRED)
# ===========================================
# Get these from https://developer.schwab.com/ after app approval
SCHWAB_APP_KEY=your_app_key_here
SCHWAB_APP_SECRET=your_app_secret_here

# Callback URL (must match what you set in Schwab Developer portal)
CALLBACK_URL=https://127.0.0.1

# ===========================================
# DISCORD WEBHOOKS (REQUIRED)
# ===========================================
# Primary webhook - where all trade notifications go
DISCORD_WEBHOOK=https://discord.com/api/webhooks/your_webhook_here

# Secondary webhook (OPTIONAL) - for cross-posting to another channel
# Leave blank or remove if not using
DISCORD_WEBHOOK_2=

# Role to @mention when trades post (OPTIONAL)
# Get this by right-clicking the role > Copy Role ID
DISCORD_ROLE_ID=

# ===========================================
# GOOGLE SHEETS (OPTIONAL)
# ===========================================
# Only needed if you want automatic weekly exports to Google Sheets
# GOOGLE_SHEETS_CREDENTIALS_PATH=/data/your-credentials.json
# GOOGLE_SHEETS_SPREADSHEET_ID=your_spreadsheet_id_here
```

**Save and close Notepad (Ctrl+S)**

### Step 6.2: Verify Base Config Exists

The base config file should already exist:
```powershell
type config\schwab-to-discord.env
```

**You should see configuration like:**
```
APP_NAME=Schwab to Discord
LOG_LEVEL=INFO
TIME_DELTA_DAYS=7
POLL_INTERVAL_SECONDS=5
...
```

**Don't edit this file unless you know what you're doing.**

### Step 6.3: Create Data Folder (If Missing)

```powershell
cd C:\Users\YourUsername\stockbot-docker\schwab-to-discord
if (!(Test-Path "data")) { mkdir data }
```

### Verify Configuration

```powershell
type config\.env.secrets | findstr "SCHWAB_APP_KEY"
```

**Should show your app key (confirm it's not the placeholder text)**

---

## Part 7: First-Time Schwab Authentication

The Schwab API uses OAuth 2.0. The first time you run the bot, you need to authorize it to access your Schwab account.

### How OAuth Works

1. Bot opens a browser to Schwab login
2. You log in and authorize the app
3. Schwab redirects to `https://127.0.0.1` with a code
4. Bot captures the code and exchanges it for tokens
5. Tokens are saved to `/data/tokens.db`
6. Future runs use saved tokens (auto-refresh)

### Step 7.1: Run the Bot for First-Time Auth

**Make sure Docker is running first!**

```powershell
cd C:\Users\YourUsername\stockbot-docker\schwab-to-discord
docker compose up --build
```

### Step 7.2: Watch for the Auth Prompt

**In the terminal, you'll see something like:**
```
Starting Schwab to Discord...
Loading configuration...
Initializing Schwab client...
Opening browser for Schwab authentication...
Please log in and authorize the application.
Waiting for callback...
```

**A browser window should open to Schwab login**

### Step 7.3: Complete Schwab Login

1. Log in with your Schwab credentials
2. You may see a security verification (text code, etc.)
3. Review the permissions the app is requesting
4. Click "Allow" or "Authorize"

### Step 7.4: Handle the Redirect

**After authorizing, Schwab redirects to `https://127.0.0.1`**

**Your browser will show an error page** - this is NORMAL!

**Look at the URL bar - it will look like:**
```
https://127.0.0.1/?code=LONG_CODE_HERE&session=xyz
```

### Step 7.5: Copy the Authorization Code

**Two methods:**

**Method A: Automatic (if schwabdev handles it)**
- Some versions auto-capture the code
- Check the terminal - if it says "Authenticated successfully", you're done

**Method B: Manual (if needed)**
1. Copy the ENTIRE URL from the browser
2. Paste it into the terminal when prompted
3. Press Enter

### Step 7.6: Verify Authentication

**In the terminal, you should see:**
```
Authentication successful!
Tokens saved to /data/tokens.db
Starting main loop...
```

### Tokens are Now Saved

- Tokens stored in `data/tokens.db`
- Bot will auto-refresh tokens as needed
- You won't need to re-authenticate unless tokens expire completely (rare)

---

## Part 8: Build and Run

### Step 8.1: Make Sure Docker is Running

**Look for the Docker whale icon in your system tray**

If not running, double-click Docker Desktop and wait.

### Step 8.2: Navigate to Project

```powershell
cd C:\Users\YourUsername\stockbot-docker\schwab-to-discord
```

### Step 8.3: Build and Run (Foreground)

**First time or after changes:**
```powershell
docker compose up --build
```

**After first build:**
```powershell
docker compose up
```

### Step 8.4: Run in Background (Recommended for 24/7)

```powershell
docker compose up -d
```

### Expected Startup Output

```
[+] Running 1/1
 ✔ Container schwab-to-discord  Created
Attaching to schwab-to-discord
schwab-to-discord  | 2024-01-15 10:30:00 INFO Starting Schwab to Discord...
schwab-to-discord  | 2024-01-15 10:30:01 INFO Loading configuration...
schwab-to-discord  | 2024-01-15 10:30:02 INFO Initializing database...
schwab-to-discord  | 2024-01-15 10:30:03 INFO Connected to Schwab API
schwab-to-discord  | 2024-01-15 10:30:04 INFO Starting main loop (poll every 5s)...
schwab-to-discord  | 2024-01-15 10:30:05 INFO Fetched 0 new orders
```

### Step 8.5: Stop the Bot

**If running in foreground:** Press `Ctrl+C`

**If running in background:**
```powershell
docker compose down
```

---

## Part 9: Verify It's Working

### Check 1: Container is Running

```powershell
docker ps
```

**Expected:**
```
CONTAINER ID   IMAGE                STATUS          NAMES
abc123         schwab-to-discord    Up 5 minutes    schwab-to-discord
```

### Check 2: View Logs

```powershell
docker logs schwab-to-discord
```

**Or follow in real-time:**
```powershell
docker logs -f schwab-to-discord
```

### Check 3: Database Created

```powershell
dir data\
```

**Should see:**
```
trades.db       (SQLite database)
tokens.db       (OAuth tokens)
```

### Check 4: Make a Test Trade

1. Go to your Schwab account
2. Make a small test trade (buy 1 share of something cheap)
3. Wait for it to fill
4. Within 5-60 seconds, you should see a Discord notification

### Check 5: Discord Message Appears

**Your Discord channel should show a message like:**
```
[Embed]
BUY: AAPL
Quantity: 1
Price: $185.50
Status: FILLED
```

---

## Part 10: Optional - Google Sheets Export

If you want automatic weekly exports to Google Sheets:

### Step 10.1: Create Google Cloud Project

1. Go to: https://console.cloud.google.com/
2. Create a new project
3. Enable "Google Sheets API" and "Google Drive API"

### Step 10.2: Create Service Account

1. Go to IAM & Admin > Service Accounts
2. Create service account
3. Download JSON credentials file
4. Rename to something memorable (e.g., `gsheet-credentials.json`)

### Step 10.3: Place Credentials File

```powershell
copy path\to\gsheet-credentials.json C:\Users\YourUsername\stockbot-docker\schwab-to-discord\data\
```

### Step 10.4: Create Google Sheet & Share

1. Create a new Google Sheet
2. Copy the Spreadsheet ID from the URL
   - URL: `https://docs.google.com/spreadsheets/d/SPREADSHEET_ID_HERE/edit`
3. Share the sheet with the service account email (found in JSON file)

### Step 10.5: Update Config

**Edit `config/.env.secrets`:**
```ini
GOOGLE_SHEETS_CREDENTIALS_PATH=/data/gsheet-credentials.json
GOOGLE_SHEETS_SPREADSHEET_ID=your_spreadsheet_id_here
GOOGLE_SHEETS_WORKSHEET_NAME=Sheet1
GSHEET_EXPORT_DAY=sat
GSHEET_EXPORT_HOUR=8
GSHEET_EXPORT_MINUTE=0
```

### Step 10.6: Restart Bot

```powershell
docker compose down
docker compose up -d
```

---

## Troubleshooting

### Problem: "SCHWAB_APP_KEY not set"

**Cause:** Secrets file missing or not loaded

**Solution:**
1. Verify file exists: `dir config\.env.secrets`
2. Check for typos in variable names
3. Ensure no spaces around `=` signs
4. Rebuild: `docker compose up --build`

---

### Problem: "Authentication failed" or "Invalid credentials"

**Cause:** Wrong Schwab app credentials or app not approved

**Solution:**
1. Go to https://developer.schwab.com/
2. Check your app status - must be "Approved"
3. Verify App Key and Secret are correct (copy fresh)
4. Ensure Callback URL is exactly `https://127.0.0.1`

---

### Problem: "Token expired" or "Refresh token failed"

**Cause:** OAuth tokens expired and couldn't refresh

**Solution:**
1. Delete old tokens: `del data\tokens.db`
2. Restart bot: `docker compose up`
3. Re-authenticate when prompted

---

### Problem: Browser doesn't open for auth

**Cause:** Running in Docker without display access

**Solution - Manual Auth:**
1. Look at the terminal output for a URL
2. Copy the URL and paste in your browser manually
3. Complete login and authorization
4. Copy the redirect URL back to the terminal

---

### Problem: "Discord webhook failed"

**Cause:** Invalid webhook URL

**Solution:**
1. Go to Discord channel settings > Integrations > Webhooks
2. Delete the old webhook, create a new one
3. Copy the full URL (starts with `https://discord.com/api/webhooks/`)
4. Update `config/.env.secrets`
5. Restart: `docker compose restart`

---

### Problem: No trades appearing in Discord

**Cause:** Multiple possible reasons

**Check 1 - Are there filled orders?**
- Log into Schwab and check "Orders" > "Filled"
- The bot only posts FILLED orders

**Check 2 - Check TIME_DELTA_DAYS**
- Default is 7 days
- If your orders are older, increase this in `config/schwab-to-discord.env`

**Check 3 - Check the logs**
```powershell
docker logs schwab-to-discord | findstr "order"
```

**Check 4 - Has it already been posted?**
- Each order is only posted ONCE
- Check `data/trades.db` if you have SQLite tools

---

### Problem: "Database locked"

**Cause:** Multiple processes accessing the database

**Solution:**
1. Stop the bot: `docker compose down`
2. Make sure no other application is using `data/trades.db`
3. Restart: `docker compose up -d`

---

### Problem: "Rate limit exceeded" (Discord 429 error)

**Cause:** Too many messages sent too quickly

**Solution:**
- The bot has built-in rate limiting
- If this happens frequently, increase `POLL_INTERVAL_SECONDS` to 10 or 15
- Check if you have a lot of back-dated orders flooding in

---

### Problem: Docker won't start / WSL error

**Cause:** WSL 2 not installed or configured

**Solution:**
```powershell
# Run as Administrator
wsl --install
# Restart computer
# Try Docker again
```

---

### Problem: "No module named 'schwabdev'"

**Cause:** Dependencies not installed

**Solution:**
```powershell
docker compose build --no-cache
docker compose up
```

---

### Problem: Cost basis / gain % showing wrong

**Cause:** LIFO matching doesn't have historical data

**Explanation:**
- The bot uses LIFO (Last-In-First-Out) for cost basis
- If you had existing positions before running the bot, it won't know their cost
- First sell of an existing position will show "No matching lot found"

**Solution:**
- This is expected behavior for positions opened before the bot started
- Future trades will track correctly

---

## Alternative Methods

### Alternative: Run Without Docker (Python Directly)

**Step 1: Install Python 3.12**
```
https://www.python.org/downloads/
```
- Download Python 3.12.x
- CHECK "Add Python to PATH"

**Step 2: Create virtual environment**
```powershell
cd C:\Users\YourUsername\stockbot-docker\schwab-to-discord
python -m venv .venv
.venv\Scripts\activate
```

**Step 3: Install dependencies**
```powershell
pip install -r requirements.txt
pip install -e .
pip install openpyxl
```

**Step 4: Set environment variables**
```powershell
# Create a .env file in the root folder with all your variables
# Or set them in PowerShell:
$env:SCHWAB_APP_KEY="your_key"
$env:SCHWAB_APP_SECRET="your_secret"
$env:DISCORD_WEBHOOK="your_webhook"
$env:DB_PATH="./data/trades.db"
$env:TOKENS_DB="./data/tokens.db"
```

**Step 5: Run**
```powershell
python main.py
```

---

### Alternative: View Logs in Docker Desktop GUI

1. Open Docker Desktop
2. Click "Containers"
3. Click on "schwab-to-discord"
4. Click "Logs" tab

---

### Alternative: Use VS Code for Editing

1. Install VS Code
2. Open the project folder
3. Edit config files with syntax highlighting
4. Use the integrated terminal

---

## Quick Reference

### Common Commands

| Action | Command |
|--------|---------|
| Start bot (foreground) | `docker compose up` |
| Start bot (background) | `docker compose up -d` |
| Stop bot | `docker compose down` |
| View logs | `docker logs -f schwab-to-discord` |
| Restart | `docker compose restart` |
| Rebuild | `docker compose up --build` |
| Check status | `docker ps` |

### File Locations

| File | Location |
|------|----------|
| Base config | `config/schwab-to-discord.env` |
| Secrets | `config/.env.secrets` |
| Database | `data/trades.db` |
| OAuth tokens | `data/tokens.db` |
| Excel export | `data/trades.xlsx` |

### Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| SCHWAB_APP_KEY | Yes | Schwab API app key |
| SCHWAB_APP_SECRET | Yes | Schwab API secret |
| DISCORD_WEBHOOK | Yes | Discord webhook URL |
| DISCORD_WEBHOOK_2 | No | Secondary webhook |
| DISCORD_ROLE_ID | No | Role to @mention |
| TIME_DELTA_DAYS | No | Days back to fetch (default: 7) |
| POLL_INTERVAL_SECONDS | No | Check interval (default: 5) |

### API Account Reference

| Service | Where to Sign Up | What You Need |
|---------|------------------|---------------|
| Schwab Developer | developer.schwab.com | App Key + Secret |
| Discord | Your server | Webhook URL |
| Google Sheets | console.cloud.google.com | Service account JSON (optional) |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│                 SCHWAB-TO-DISCORD               │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌─────────┐    ┌─────────┐    ┌─────────────┐ │
│  │ Schwab  │───▶│   Bot   │───▶│   Discord   │ │
│  │   API   │    │  Logic  │    │   Webhook   │ │
│  └─────────┘    └────┬────┘    └─────────────┘ │
│                      │                          │
│                 ┌────▼────┐                     │
│                 │ SQLite  │                     │
│                 │   DB    │                     │
│                 └─────────┘                     │
│                                                 │
│  Poll every 5s ──▶ Dedupe ──▶ Post to Discord  │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

## Need More Help?

1. Check logs: `docker logs schwab-to-discord`
2. Read `docs/env.md` for all environment variables
3. Check `README.md` for quick start
4. Look at `src/app/bot.py` for main logic

---

*Last updated: February 2026*
