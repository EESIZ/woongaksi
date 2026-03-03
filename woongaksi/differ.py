"""JSON 캐시 기반 변경 감지."""

import json
import logging
import os

log = logging.getLogger(__name__)


class DiffResult:
    """DB 변경 결과 컨테이너."""

    __slots__ = ("added", "removed", "modified")

    def __init__(self, added=None, removed=None, modified=None):
        self.added = added or []
        self.removed = removed or []
        self.modified = modified or []

    @property
    def has_changes(self) -> bool:
        return bool(self.added or self.removed or self.modified)

    def __repr__(self):
        return f"DiffResult(+{len(self.added)} -{len(self.removed)} ~{len(self.modified)})"


def _cache_path(cache_dir: str, db_name: str) -> str:
    return os.path.join(cache_dir, f"{db_name}_state.json")


def load_cache(cache_dir: str, db_name: str) -> dict:
    """이전 캐시 로드. 캐시 없으면 빈 dict 반환."""
    path = _cache_path(cache_dir, db_name)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        log.warning("캐시 읽기 실패 [%s]: %s", db_name, e)
        return {}


def save_cache(cache_dir: str, db_name: str, items: list[dict]) -> dict:
    """현재 상태를 {page_id: item_dict}로 저장."""
    os.makedirs(cache_dir, exist_ok=True)
    state = {item["id"]: item for item in items}
    path = _cache_path(cache_dir, db_name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    return state


def compute_diff(old_state: dict, new_items: list[dict]) -> DiffResult:
    """이전 캐시와 새 데이터를 비교하여 차이를 계산."""
    new_state = {item["id"]: item for item in new_items}
    old_ids = set(old_state.keys())
    new_ids = set(new_state.keys())

    added = [new_state[pid] for pid in (new_ids - old_ids)]
    removed = [old_state[pid] for pid in (old_ids - new_ids)]

    modified = []
    for pid in old_ids & new_ids:
        old_item = old_state[pid]
        new_item = new_state[pid]
        changes = {}
        all_keys = set(old_item.keys()) | set(new_item.keys())
        all_keys.discard("id")
        for key in all_keys:
            old_val = old_item.get(key)
            new_val = new_item.get(key)
            if old_val != new_val:
                changes[key] = {"old": old_val, "new": new_val}
        if changes:
            modified.append({"item": new_item, "changes": changes})

    return DiffResult(added=added, removed=removed, modified=modified)
