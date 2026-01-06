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

def load_config() -> Config:
    return Config(
        app_name=os.environ["APP_NAME"],
        schwab_app_key=os.environ["SCHWAB_APP_KEY"],
        schwab_app_secret = os.environ["SCHWAB_APP_SECRET"],
        discord_channel=os.environ["DISCORD_CHANNEL_ID"],
        discord_webhook=os.environ["DISCORD_WEBHOOK"],
        db_path=os.getenv("DB_PATH", "data/app.db"),
    )
