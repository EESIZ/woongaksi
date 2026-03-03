"""APScheduler 오케스트레이터 — 전체 DB 폴링 관리."""

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from .client import query_database
from .config import Config
from .differ import load_cache, save_cache, compute_diff
from .formatter import format_changes
from .telegram import send_message

log = logging.getLogger(__name__)


def _poll_db(cfg: Config, db_config: dict):
    """단일 DB 폴링 → 캐시 비교 → 변경 시 알림."""
    db_name = db_config["name"]

    try:
        new_items = query_database(cfg.notion_api_key, db_config)
        log.info("[%s] %d건 조회", db_name, len(new_items))
    except Exception as e:
        log.error("[%s] Notion 조회 실패: %s", db_name, e)
        return

    old_state = load_cache(cfg.cache_dir, db_name)

    if not old_state:
        log.info("[%s] 최초 실행, 캐시 시딩 (%d건)", db_name, len(new_items))
        save_cache(cfg.cache_dir, db_name, new_items)
        return

    diff = compute_diff(old_state, new_items)

    if diff.has_changes:
        log.info("[%s] 변경 감지: %s", db_name, diff)
        message = format_changes(db_config, diff)
        send_message(cfg.telegram_bot_token, cfg.telegram_chat_id, message)
    else:
        log.debug("[%s] 변경 없음", db_name)

    save_cache(cfg.cache_dir, db_name, new_items)


def poll_and_notify(cfg: Config):
    """전체 DB 폴링 + 알림 전송."""
    log.info("폴링 시작 (%d개 DB)...", len(cfg.databases))
    for db_config in cfg.databases:
        _poll_db(cfg, db_config)
    log.info("폴링 완료")


def create_scheduler(cfg: Config) -> BackgroundScheduler:
    """APScheduler 생성."""
    sched = BackgroundScheduler(daemon=True)
    sched.add_job(
        poll_and_notify,
        args=[cfg],
        trigger="interval",
        minutes=cfg.poll_interval,
        id="woongaksi_poll",
        name="Notion Polling",
        max_instances=1,
    )
    return sched
