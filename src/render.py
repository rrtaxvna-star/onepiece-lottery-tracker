"""Renders the static listing page for GitHub Pages from DB rows."""
from datetime import datetime, timezone, timedelta
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "docs" / "index.html"

JST = timezone(timedelta(hours=9))


def render(rows: list) -> None:
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template("index.html.j2")

    now = datetime.now(JST)
    items = []
    for row in rows:
        deadline_raw = row["apply_deadline"]
        is_urgent = False
        if deadline_raw:
            try:
                deadline = datetime.fromisoformat(deadline_raw)
                if deadline.tzinfo is None:
                    deadline = deadline.replace(tzinfo=JST)
                is_urgent = deadline - now <= timedelta(hours=24)
            except ValueError:
                pass
        items.append({**dict(row), "is_urgent": is_urgent})

    html = template.render(items=items, generated_at=now.strftime("%Y-%m-%d %H:%M JST"))
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(html, encoding="utf-8")
