"""Notion API 클라이언트 — 모든 DB 스키마에 범용 대응."""

import logging

import requests

log = logging.getLogger(__name__)

NOTION_VERSION = "2022-06-28"


def _make_headers(api_key: str) -> dict:
    return {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def _extract_value(prop: dict) -> object:
    """Notion 프로퍼티 객체에서 평문 값 추출."""
    ptype = prop.get("type", "")

    if ptype == "title":
        items = prop.get("title", [])
        return items[0].get("plain_text", "") if items else ""
    if ptype == "rich_text":
        items = prop.get("rich_text", [])
        return items[0].get("plain_text", "") if items else ""
    if ptype == "select":
        sel = prop.get("select")
        return sel.get("name", "") if sel else ""
    if ptype == "multi_select":
        return ", ".join(s.get("name", "") for s in prop.get("multi_select", []))
    if ptype == "date":
        d = prop.get("date")
        return d.get("start", "") if d else ""
    if ptype == "number":
        return prop.get("number")
    if ptype == "checkbox":
        return prop.get("checkbox", False)
    if ptype == "status":
        s = prop.get("status")
        return s.get("name", "") if s else ""
    if ptype == "url":
        return prop.get("url", "")
    if ptype == "email":
        return prop.get("email", "")
    if ptype == "phone_number":
        return prop.get("phone_number", "")
    if ptype == "people":
        return ", ".join(p.get("name", "") for p in prop.get("people", []))
    if ptype == "relation":
        return [r.get("id", "") for r in prop.get("relation", [])]
    if ptype == "formula":
        formula = prop.get("formula", {})
        ftype = formula.get("type", "")
        return formula.get(ftype)
    if ptype == "rollup":
        rollup = prop.get("rollup", {})
        rtype = rollup.get("type", "")
        return rollup.get(rtype)

    return None


def query_database(api_key: str, db_config: dict) -> list[dict]:
    """Notion DB를 조회하고 추출된 아이템 리스트를 반환.

    Args:
        api_key: Notion integration 토큰
        db_config: config.yaml의 database 항목 dict

    Returns:
        [{"id": "page-id", "title": "...", "프로퍼티명": 값, ...}, ...]
    """
    db_id = db_config["id"]
    title_prop = db_config.get("title_property", "Name")
    tracked = db_config.get("tracked_properties", [])
    notion_filter = db_config.get("filter")

    url = f"https://api.notion.com/v1/databases/{db_id}/query"
    headers = _make_headers(api_key)
    all_results = []
    body = {}

    if notion_filter:
        body["filter"] = notion_filter

    while True:
        resp = requests.post(url, json=body, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        all_results.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        body["start_cursor"] = data["next_cursor"]

    items = []
    for page in all_results:
        props = page.get("properties", {})
        item = {"id": page["id"]}

        # 제목 추출
        if title_prop in props:
            item["title"] = _extract_value(props[title_prop])
        else:
            for key, val in props.items():
                if val.get("type") == "title":
                    item["title"] = _extract_value(val)
                    break
            else:
                item["title"] = ""

        # 추적 프로퍼티 추출
        if tracked:
            for prop_name in tracked:
                if prop_name in props:
                    item[prop_name] = _extract_value(props[prop_name])
        else:
            for key, val in props.items():
                if key == title_prop:
                    continue
                extracted = _extract_value(val)
                if extracted is not None and extracted != "" and extracted != []:
                    item[key] = extracted

        items.append(item)

    return items
