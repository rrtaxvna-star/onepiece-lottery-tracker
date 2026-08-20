"""Notification backends. Discord today; Slack/LINE can implement the same
interface later without touching main.py."""
import os
from abc import ABC, abstractmethod

import requests


class Notifier(ABC):
    @abstractmethod
    def send(self, message: str) -> None: ...


class DiscordNotifier(Notifier):
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send(self, message: str) -> None:
        resp = requests.post(self.webhook_url, json={"content": message}, timeout=10)
        resp.raise_for_status()


class NullNotifier(Notifier):
    """Used when no webhook is configured, e.g. local dry runs."""

    def send(self, message: str) -> None:
        print(f"[notify:skipped] {message}")


def get_notifier() -> Notifier:
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if webhook_url:
        return DiscordNotifier(webhook_url)
    return NullNotifier()


def format_new_listing(item: dict) -> str:
    return (
        f"🆕 **新規抽選告知検知**\n"
        f"商品: {item['product_name']}\n"
        f"店舗: {item['store_name']}\n"
        f"締切: {item.get('apply_deadline') or '不明'}\n"
        f"応募方法: {item.get('apply_method') or '不明'}\n"
        f"詳細: {item.get('source_url')}"
    )


def format_deadline_reminder(item: dict) -> str:
    return (
        f"⏰ **締切24時間前**\n"
        f"商品: {item['product_name']}\n"
        f"店舗: {item['store_name']}\n"
        f"締切: {item.get('apply_deadline')}\n"
        f"詳細: {item.get('source_url')}"
    )
