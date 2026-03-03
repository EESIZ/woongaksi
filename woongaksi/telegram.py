"""Telegram Bot API 전송 — 재시도 + 자동 분할."""

import logging
import time

import requests

log = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds
MAX_MESSAGE_LENGTH = 4096  # Telegram 제한


def send_message(token: str, chat_id: str, text: str, parse_mode: str = "HTML") -> bool:
    """텔레그램 메시지 전송. 4096자 초과 시 자동 분할."""
    if len(text) <= MAX_MESSAGE_LENGTH:
        return _send_single(token, chat_id, text, parse_mode)

    chunks = _split_message(text, MAX_MESSAGE_LENGTH)
    ok = True
    for chunk in chunks:
        if not _send_single(token, chat_id, chunk, parse_mode):
            ok = False
    return ok


def _send_single(token: str, chat_id: str, text: str, parse_mode: str) -> bool:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.post(url, json=payload, timeout=15)
            if resp.status_code == 200:
                log.info("텔레그램 전송 완료 (%d자)", len(text))
                return True
            log.warning(
                "텔레그램 API %d: %s (시도 %d/%d)",
                resp.status_code, resp.text[:200], attempt, MAX_RETRIES,
            )
        except requests.RequestException as e:
            log.warning("텔레그램 전송 오류: %s (시도 %d/%d)", e, attempt, MAX_RETRIES)

        if attempt < MAX_RETRIES:
            time.sleep(RETRY_DELAY)

    log.error("텔레그램 전송 실패 (%d회 시도 후)", MAX_RETRIES)
    return False


def _split_message(text: str, limit: int) -> list[str]:
    """줄바꿈 기준으로 메시지 분할."""
    chunks = []
    while len(text) > limit:
        split_at = text.rfind("\n", 0, limit)
        if split_at <= 0:
            split_at = limit
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    if text:
        chunks.append(text)
    return chunks
