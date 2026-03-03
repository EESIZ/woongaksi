#!/usr/bin/env python3
"""노션우렁각시 데몬 진입점.

Usage:
    woongaksi                              # config.yaml 자동 탐색
    woongaksi --config /path/to/config.yaml
    python -m woongaksi -c config.yaml
"""

import argparse
import datetime
import logging
import os
import signal
import sys
import time

from .config import load_config
from .scheduler import create_scheduler, poll_and_notify


def setup_logging(log_path):
    """KST 타임스탬프 로깅 설정."""
    if log_path:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)

    KST = datetime.timezone(datetime.timedelta(hours=9))

    class KSTFormatter(logging.Formatter):
        def formatTime(self, record, datefmt=None):
            dt = datetime.datetime.fromtimestamp(record.created, tz=KST)
            return dt.strftime(datefmt or "%Y-%m-%d %H:%M:%S")

    fmt = KSTFormatter(
        "[%(asctime)s KST] %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(stream_handler)

    if log_path:
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(fmt)
        root.addHandler(file_handler)


def main():
    parser = argparse.ArgumentParser(
        prog="woongaksi",
        description="노션우렁각시 — AI 에이전트를 위한 Notion 변경 릴레이 데몬",
    )
    parser.add_argument(
        "-c", "--config",
        default=os.environ.get("WOONGAKSI_CONFIG", "config.yaml"),
        help="설정 파일 경로 (기본: config.yaml 또는 $WOONGAKSI_CONFIG)",
    )
    args = parser.parse_args()

    cfg = load_config(args.config)
    setup_logging(cfg.log_path)

    log = logging.getLogger("woongaksi")
    log.info("=== 노션우렁각시 v%s 시작 ===", cfg.version)
    log.info("모니터링 DB %d개, 폴링 간격 %d분", len(cfg.databases), cfg.poll_interval)

    for db in cfg.databases:
        log.info("  %s %s [%s...]", db["emoji"], db["label"], db["id"][:8])

    # 최초 1회 즉시 폴링 (캐시 시딩)
    log.info("최초 폴링 실행...")
    poll_and_notify(cfg)

    # 스케줄러 시작
    sched = create_scheduler(cfg)
    sched.start()
    log.info("스케줄러 시작. 다음 폴링 %d분 후.", cfg.poll_interval)

    # Graceful shutdown
    def shutdown(signum, _frame):
        sig_name = signal.Signals(signum).name
        log.info("%s 수신, 종료합니다...", sig_name)
        sched.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        log.info("종료.")
        sched.shutdown(wait=False)


if __name__ == "__main__":
    main()
