from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    GMGN_ACCESS_TOKEN: str = ""
    SQLITE_PATH: str = "./data/zook.db"
    RATE_REQ_PER_SEC: float = 2.0
    RATE_BURST: int = 5
    POLL_INTERVAL_SECONDS: int = 30
    LOG_LEVEL: str = "INFO"


settings = Settings()
