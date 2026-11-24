"""集中配置与启动校验：所有配置来自环境变量，缺失时快速失败。"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


class ConfigError(RuntimeError):
    """配置错误。"""


def _int(name: str, default: int, minimum: int = 1, maximum: int = 65535) -> int:
    raw = os.getenv(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} 必须是整数，当前为 {raw!r}") from exc
    if not minimum <= value <= maximum:
        raise ConfigError(f"{name} 必须在 [{minimum}, {maximum}] 之间，当前为 {value}")
    return value


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    db_path: str
    log_level: str
    app_env: str
    cors_origins: tuple[str, ...]
    request_timeout_s: int

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


def load_settings() -> Settings:
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    if app_env not in {"development", "testing", "production"}:
        raise ConfigError(f"APP_ENV 取值非法: {app_env}")

    origins_raw = os.getenv("CORS_ORIGINS", "http://localhost:8787,http://127.0.0.1:8787")
    origins = tuple(o.strip() for o in origins_raw.split(",") if o.strip())
    if app_env == "production" and "*" in origins:
        raise ConfigError("生产环境禁止使用通配符 CORS 来源")

    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    if log_level not in {"DEBUG", "INFO", "WARNING", "ERROR"}:
        raise ConfigError(f"LOG_LEVEL 取值非法: {log_level}")

    db_path = os.getenv("DB_PATH", "data/agentops.db")
    parent = Path(db_path).parent
    if parent and not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)

    return Settings(
        host=os.getenv("HOST", "127.0.0.1"),
        port=_int("PORT", 8787),
        db_path=db_path,
        log_level=log_level,
        app_env=app_env,
        cors_origins=origins,
        request_timeout_s=_int("REQUEST_TIMEOUT_S", 30),
    )
