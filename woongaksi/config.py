"""설정 로더 — YAML 파일 + 환경변수를 병합."""

import os
import sys
from dataclasses import dataclass, field

import yaml


@dataclass
class Config:
    version: str = "0.1.0"
    notion_api_key: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    poll_interval: int = 5
    log_path: str = ""
    cache_dir: str = ""
    databases: list = field(default_factory=list)


def load_config(config_path: str) -> Config:
    """YAML + 환경변수에서 설정 로드.

    환경변수가 YAML 값을 덮어씁니다:
      NOTION_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
      WOONGAKSI_LOG, WOONGAKSI_CACHE, POLL_INTERVAL_MINUTES
    """
    cfg = Config()

    # YAML 로드
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
    else:
        raw = {}

    # DB 정의 (YAML 필수)
    cfg.databases = raw.get("databases", [])
    cfg.poll_interval = int(raw.get("poll_interval_minutes", 5))

    # DB 엔트리 기본값 보정
    for i, db in enumerate(cfg.databases):
        db.setdefault("name", f"db_{i}")
        db.setdefault("emoji", "📄")
        db.setdefault("label", db["name"])
        db.setdefault("title_property", "Name")
        db.setdefault("tracked_properties", [])
        db.setdefault("filter", None)
        if "id" not in db:
            print(f"[ERROR] databases[{i}] '{db['name']}'에 'id'가 없습니다", file=sys.stderr)
            sys.exit(1)

    # 환경변수 (시크릿은 반드시 환경변수로)
    cfg.notion_api_key = os.environ.get("NOTION_API_KEY", "")
    cfg.telegram_bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    cfg.telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    cfg.poll_interval = int(os.environ.get("POLL_INTERVAL_MINUTES", str(cfg.poll_interval)))
    cfg.log_path = os.environ.get("WOONGAKSI_LOG", "/tmp/woongaksi.log")
    cfg.cache_dir = os.environ.get("WOONGAKSI_CACHE", os.path.join(os.getcwd(), "cache"))

    # 필수값 검증
    missing = []
    if not cfg.notion_api_key:
        missing.append("NOTION_API_KEY")
    if not cfg.telegram_bot_token:
        missing.append("TELEGRAM_BOT_TOKEN")
    if not cfg.telegram_chat_id:
        missing.append("TELEGRAM_CHAT_ID")
    if not cfg.databases:
        missing.append("databases (config.yaml에 정의 필요)")

    if missing:
        print(f"[ERROR] 누락된 설정: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    return cfg
