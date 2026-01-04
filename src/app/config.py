from dataclasses import dataclass
import os

@dataclass(frozen=True)
class Config:
    schwab_app_key: str
    schwab_app_secret: str
    discord_webhook: str
    discord_channel: str
    db_path: str

def load_config() -> Config:
    return Config(
        schwab_app_key=os.environ["SCHWAB_APP_KEY"],
        schwab_app_secret = os.environ["SCHWAB_APP_SECRET"],
        discord_webhook=os.environ["DISCORD_WEBHOOK"],
        discord_channel=os.environ["DISCORD_CHANNEL_ID"],
        db_path=os.getenv("DB_PATH", "data/app.db"),
    )
