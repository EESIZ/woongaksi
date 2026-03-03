"""변경사항 → 텔레그램 HTML 포맷터.

어떤 DB 스키마든 범용 대응 — db_config의 emoji, label 사용.
"""


def _escape_html(text) -> str:
    if not isinstance(text, str):
        text = str(text) if text is not None else ""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _format_value(value) -> str:
    if value is None or value == "":
        return "—"
    if isinstance(value, bool):
        return "✓" if value else "✗"
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    return _escape_html(value)


def format_changes(db_config: dict, diff) -> str:
    """DiffResult를 텔레그램 HTML로 변환."""
    emoji = db_config.get("emoji", "📄")
    label = db_config.get("label", db_config.get("name", "DB"))

    lines = [f"{emoji} <b>{_escape_html(label)} 변경</b>"]

    if diff.added:
        lines.append("")
        lines.append("🆕 추가:")
        for item in diff.added:
            lines.append(_format_item_summary(item))

    if diff.removed:
        lines.append("")
        lines.append("❌ 삭제:")
        for item in diff.removed:
            title = _escape_html(item.get("title", "제목 없음"))
            lines.append(f"  • <b>{title}</b>")

    if diff.modified:
        lines.append("")
        lines.append("✏️ 변경:")
        for mod in diff.modified:
            title = _escape_html(mod["item"].get("title", "제목 없음"))
            change_parts = []
            for key, change in mod["changes"].items():
                if key == "title":
                    change_parts.append(
                        f"제목 {_format_value(change['old'])} → {_format_value(change['new'])}"
                    )
                else:
                    change_parts.append(
                        f"{_escape_html(key)} {_format_value(change['old'])} → {_format_value(change['new'])}"
                    )
            lines.append(f"  • <b>{title}</b>: {', '.join(change_parts)}")

    return "\n".join(lines)


def _format_item_summary(item: dict) -> str:
    """아이템 한 줄 요약."""
    title = _escape_html(item.get("title", "제목 없음"))
    details = []
    for key, val in item.items():
        if key in ("id", "title"):
            continue
        if val is not None and val != "" and val != []:
            details.append(f"{_escape_html(key)}: {_format_value(val)}")
    detail_str = f" ({', '.join(details)})" if details else ""
    return f"  • <b>{title}</b>{detail_str}"
