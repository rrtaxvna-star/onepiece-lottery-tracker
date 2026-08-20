"""Orchestration entrypoint, run on a schedule by GitHub Actions.

Flow: scrape -> extract (Claude) -> filter (1都3県/オンライン) -> dedup against
SQLite -> notify (new / 24h-before-deadline) -> archive past-deadline items ->
render static page for GitHub Pages.
"""
import hashlib
import sys
from datetime import datetime, timedelta, timezone

import db
import extractor
import filters
import notifier
import render
import scraper

JST = timezone(timedelta(hours=9))


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main() -> None:
    now = datetime.now(JST)
    now_iso = now.isoformat()
    threshold_iso = (now + timedelta(hours=24)).isoformat()

    print("Discovering articles...")
    article_urls = scraper.discover_article_urls()
    if not article_urls:
        print("No ONE PIECE-related articles found this run.", file=sys.stderr)

    articles = scraper.fetch_all(article_urls)
    n = notifier.get_notifier()

    with db.connect() as conn:
        all_items: list[dict] = []
        for url, text in articles.items():
            content_hash = _content_hash(text)
            if content_hash == db.get_source_hash(conn, url):
                print(f"Unchanged, skipping extraction: {url}")
                continue

            print(f"Extracting from {url} ({len(text)} chars)...")
            try:
                listings = extractor.extract_listings(url, text)
            except Exception as exc:  # noqa: BLE001 - keep the run alive for other articles
                print(f"Extraction failed for {url}: {exc}", file=sys.stderr)
                continue
            all_items.extend(listings)
            db.set_source_hash(conn, url, content_hash, now_iso)

        existing_ids = db.get_existing_ids(conn)

        new_count = 0
        for item in all_items:
            item_id = db.listing_id(
                item["product_name"], item["store_name"], item.get("apply_deadline") or ""
            )
            item["id"] = item_id
            in_scope = filters.is_in_scope(item)

            if item_id in existing_ids:
                continue

            db.insert_listing(conn, item, in_scope, now_iso)
            existing_ids.add(item_id)
            new_count += 1

            if in_scope:
                n.send(notifier.format_new_listing(item))
                db.mark_notified_new(conn, item_id)

        print(f"{new_count} new listing(s) recorded this run.")

        due_soon = db.fetch_needing_24h_notice(conn, now_iso, threshold_iso)
        for row in due_soon:
            n.send(notifier.format_deadline_reminder(dict(row)))
            db.mark_notified_24h(conn, row["id"])
        print(f"{len(due_soon)} deadline-approaching notice(s) sent.")

        db.archive_past_deadline(conn, now_iso)

        active_rows = db.fetch_active(conn)

    render.render(active_rows)
    print(f"Rendered {len(active_rows)} active listing(s) to docs/index.html")


if __name__ == "__main__":
    main()
