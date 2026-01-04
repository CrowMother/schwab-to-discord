from dataclasses import dataclass
import os

@dataclass(frozen=True)
class Config:
    schwab_api_key: str
    discord_webhook: str
    db_path: str

def load_config() -> Config:
    return Config(
        schwab_api_key=os.environ["SCHWAB_API_KEY"],
        discord_webhook=os.environ["DISCORD_WEBHOOK"],
        db_path=os.getenv("DB_PATH", "data/app.db"),
    )
