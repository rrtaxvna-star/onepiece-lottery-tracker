"""Structured extraction of lottery listings from raw article text via Claude.

Uses forced tool-use so the response is guaranteed valid JSON matching our
schema, rather than parsing free-form text.
"""
import os

import anthropic

MODEL = "claude-haiku-4-5-20251001"

TOOL = {
    "name": "record_lottery_listings",
    "description": "記事本文から読み取れるワンピースカードゲームのBOX等抽選販売情報を全て構造化して記録する。",
    "input_schema": {
        "type": "object",
        "properties": {
            "listings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "product_name": {
                            "type": "string",
                            "description": "BOX名・ブースターパック名など商品名",
                        },
                        "store_name": {
                            "type": "string",
                            "description": "販売店舗名(チェーン名+支店名がわかればそのまま)",
                        },
                        "apply_start": {
                            "type": ["string", "null"],
                            "description": "応募開始日時。ISO8601 (YYYY-MM-DDTHH:MM:SS)。年が本文になければ2026年と仮定。時刻不明なら00:00とする。不明ならnull。",
                        },
                        "apply_deadline": {
                            "type": ["string", "null"],
                            "description": "応募締切日時。ISO8601。年が本文になければ2026年と仮定。時刻不明なら23:59とする。不明ならnull。",
                        },
                        "result_date": {
                            "type": ["string", "null"],
                            "description": "抽選結果発表日。わかれば記載、なければnull。",
                        },
                        "pickup_period": {
                            "type": ["string", "null"],
                            "description": "購入・受け取り可能期間。わかれば記載、なければnull。",
                        },
                        "apply_method": {
                            "type": "string",
                            "description": "応募方法(例: フォロー&リポスト, 公式アプリ抽選, 専用フォーム等)",
                        },
                        "delivery_type": {
                            "type": "string",
                            "enum": ["online", "pickup", "unknown"],
                            "description": (
                                "online = 当選後オンラインで購入・自宅配送/店頭受取が不要なもの。"
                                "pickup = 当選後に実店舗へ出向いて受け取り・購入する必要があるもの。"
                                "判断できない場合はunknown。"
                            ),
                        },
                        "prefecture": {
                            "type": ["string", "null"],
                            "description": (
                                "delivery_type=pickupの場合のみ、店舗の所在都道府県を店舗名・支店名から推定して"
                                "「東京都」「神奈川県」「埼玉県」「千葉県」のように記載。他県なら実際の県名。"
                                "推定できなければnull。delivery_type=onlineの場合はnullでよい。"
                            ),
                        },
                    },
                    "required": ["product_name", "store_name", "apply_method", "delivery_type"],
                },
            }
        },
        "required": ["listings"],
    },
}

SYSTEM_PROMPT = """あなたはトレーディングカードショップの抽選販売告知記事から情報を構造化抽出する専門アシスタントです。
記事本文には複数の店舗・複数の商品の抽選情報が混在しています。record_lottery_listingsツールを使い、
本文に実際に記載されている情報のみを抽出してください。記載のない項目はnullにし、推測で埋めないでください
(ただしprefectureは店舗名からの妥当な地理的推定は許可します)。ワンピースカードゲーム以外の商品
(ポケモンカード等)の情報は無視してください。"""


def extract_listings(article_url: str, article_text: str) -> list[dict]:
    if not article_text.strip():
        return []

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    message = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        tools=[TOOL],
        tool_choice={"type": "tool", "name": "record_lottery_listings"},
        messages=[
            {
                "role": "user",
                "content": f"以下はワンピースカードゲーム抽選情報まとめ記事の本文です。\n\n{article_text[:15000]}",
            }
        ],
    )

    for block in message.content:
        if block.type == "tool_use" and block.name == "record_lottery_listings":
            listings = block.input.get("listings", [])
            for item in listings:
                item["source_url"] = article_url
            return listings
    return []
