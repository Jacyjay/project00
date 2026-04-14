from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator


BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_SQLITE_PATH = BASE_DIR / "travel_checkins.db"
DEFAULT_UPLOAD_DIR = BASE_DIR / "uploads"
LOCAL_DEV_ORIGIN_REGEX = (
    r"https?://("
    r"localhost|127(?:\.\d{1,3}){3}|0\.0\.0\.0|"
    r"10(?:\.\d{1,3}){3}|"
    r"192\.168(?:\.\d{1,3}){2}|"
    r"172\.(?:1[6-9]|2\d|3[0-1])(?:\.\d{1,3}){2}"
    r")(?::\d+)?"
)


class Settings(BaseSettings):
    DATABASE_URL: str = f"sqlite+aiosqlite:///{DEFAULT_SQLITE_PATH}"
    SECRET_KEY: str = "your-super-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    UPLOAD_DIR: str = str(DEFAULT_UPLOAD_DIR)
    BACKEND_CORS_ORIGINS: str = ""
    BACKEND_CORS_ORIGIN_REGEX: str = ""
    ALLOW_ALL_CORS: bool = False

    # 网易163邮箱 SMTP settings
    MAIL_USERNAME: str = ""          # your 163 email, e.g. example@163.com
    MAIL_PASSWORD: str = ""          # 163 mail authorization code (not login password)
    MAIL_FROM: str = ""              # same as MAIL_USERNAME
    MAIL_SERVER: str = "smtp.163.com"
    MAIL_PORT: int = 465
    MAIL_SSL: bool = True

    # Doubao AI (火山方舟)
    DOUBAO_API_KEY: str = ""
    DOUBAO_ENDPOINT_ID: str = ""

    # Amap (高德地图)
    AMAP_KEY: str = ""
    AMAP_WEB_KEY: str = ""
    MAIL_DEBUG_FALLBACK: bool = False

    model_config = SettingsConfigDict(env_file=str(BASE_DIR / ".env"), extra="ignore")

    @model_validator(mode="after")
    def resolve_paths(self) -> "Settings":
        """Always resolve filesystem-backed settings relative to BASE_DIR."""
        path = Path(self.UPLOAD_DIR)
        if not path.is_absolute():
            self.UPLOAD_DIR = str(BASE_DIR / self.UPLOAD_DIR)

        sqlite_prefixes = ("sqlite:///", "sqlite+aiosqlite:///")
        for prefix in sqlite_prefixes:
            if not self.DATABASE_URL.startswith(prefix):
                continue

            raw_path = self.DATABASE_URL[len(prefix):]
            if raw_path == ":memory:":
                break

            db_path = Path(raw_path)
            if not db_path.is_absolute():
                resolved_path = (BASE_DIR / db_path).resolve()
                self.DATABASE_URL = f"{prefix}{resolved_path}"
            break
        return self

    @property
    def cors_origins(self) -> list[str]:
        if not self.BACKEND_CORS_ORIGINS.strip():
            return []
        return [
            item.strip()
            for item in self.BACKEND_CORS_ORIGINS.split(",")
            if item.strip()
        ]

    @property
    def cors_origin_regex(self) -> str:
        if self.BACKEND_CORS_ORIGIN_REGEX.strip():
            return self.BACKEND_CORS_ORIGIN_REGEX.strip()
        if self.ALLOW_ALL_CORS:
            return r"https?://.*"
        return LOCAL_DEV_ORIGIN_REGEX

    @property
    def mail_enabled(self) -> bool:
        return bool(self.MAIL_USERNAME and self.MAIL_PASSWORD)

    @property
    def amap_web_key(self) -> str:
        return (self.AMAP_WEB_KEY or self.AMAP_KEY).strip()


settings = Settings()

# Ensure upload directory exists
Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
