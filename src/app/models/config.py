from dataclasses import dataclass
import os

@dataclass(frozen=True)
class Config:
    app_name: str
    schwab_app_key: str
    schwab_app_secret: str
    discord_webhook: str
    discord_channel: str | None
    db_path: str
    callback_url: str
    tokens_db: str
    schwab_timeout: int
    call_on_auth: str | None
    time_delta_days: int
    status: str | None

def _opt_str(key: str, alt = None) -> str | None:
    val = os.getenv(key)
    return val if val is not None and val != "" else alt

def _opt_int(key: str, alt=None) -> int | None:
    val = os.getenv(key)
    return int(val) if val is not None and val != "" else alt

def _opt_bool(key: str, alt=None) -> bool | None:
    val = os.getenv(key)
    if val is not None and val != "":
        return val.lower() in ("1", "true", "yes", "on")
    return alt

def _opt_float(key: str, alt=None) -> float | None:
    val = os.getenv(key)
    return float(val) if val is not None and val != "" else alt

def load_config() -> Config:
    return Config(
        app_name=_opt_str("APP_NAME"),
        schwab_app_key=_opt_str("SCHWAB_APP_KEY"),
        schwab_app_secret = _opt_str("SCHWAB_APP_SECRET"),
        discord_channel=_opt_str("DISCORD_CHANNEL_ID"),
        discord_webhook=_opt_str("DISCORD_WEBHOOK"),
        db_path="src/data/trades.db",
        callback_url=_opt_str("CALLBACK_URL"),
        tokens_db=_opt_str("TOKENS_DB"),
        schwab_timeout=_opt_int("SCHWAB_TIMEOUT",10),
        call_on_auth=_opt_str("CALL_ON_AUTH"),
        time_delta_days=_opt_int("TIME_DELTA_DAYS",7),
        status=_opt_str("ORDER_STATUS")
    )
def load_single_value(key: str, alt=None):
    val = os.getenv(key)
    return val if val is not None and val != "" else alt