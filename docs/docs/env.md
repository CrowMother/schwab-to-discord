# Configuration & `.env`

This app reads **all configuration from environment variables** and bundles them into a `Config` dataclass via `load_config()`.  
Local dev can use a `.env` file; production (Docker) should inject env vars at runtime.

---

## Local development

### Option A (recommended): `.env` + `python-dotenv`
1. Create **`./.env`** at the repo root (same folder as `pyproject.toml`).
2. Add `.env` to `.gitignore`.
3. Install and load dotenv once at startup (entrypoint) before calling `load_config()`:
   - `pip install python-dotenv`
   - `load_dotenv()` at app start

> Note: `python-dotenv` **does not override** env vars that are already set unless you pass `override=True`.

### Option B: VS Code `envFile`
VS Code debugging supports pointing to a workspace `.env` via `launch.json` using `envFile`.  
This is purely a dev convenience; Docker deployments shouldn’t rely on it.

---

## Docker / deployment

Do **not** bake `.env` into the image. Inject environment variables via:
- `docker run -e ...` or `--env-file ...`
- `docker compose` `environment:` / `env_file:`
- your hosting platform’s secrets/config UI

Same code path: `load_config()` always reads from env vars.

---

# Variable Modules

## Module: Schwab (required)
| Variable | Required | Type | Example |
|---|---:|---|---|
| `SCHWAB_APP_KEY` | ✅ | string | `abc123` |
| `SCHWAB_APP_SECRET` | ✅ | string | `shhh_its_a_secret` |

## Module: Discord (required)
| Variable | Required | Type | Example |
|---|---:|---|---|
| `DISCORD_WEBHOOK` | ✅ | URL string | `https://discord.com/api/webhooks/...` |
| `DISCORD_CHANNEL_ID` | ✅ | string | `123456789012345678` |

> Keep channel ID as a **string** (even though it looks numeric).

## Module: Storage / DB (optional)
| Variable | Required | Type | Default | Example |
|---|---:|---|---|---|
| `DB_PATH` | ❌ | path string | `data/app.db` | `data/app.db` |

---

## Example `.env` (repo root)

```env
# --- Schwab ---
SCHWAB_APP_KEY=your_app_key_here
SCHWAB_APP_SECRET=your_app_secret_here

# --- Discord ---
DISCORD_WEBHOOK=https://discord.com/api/webhooks/XXXXX/YYYYY
DISCORD_CHANNEL_ID=123456789012345678

# --- Storage ---
DB_PATH=data/app.db
