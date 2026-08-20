"""Scope filter: 1都3県(東京・神奈川・埼玉・千葉)の店頭受取、またはオンライン配送のみを対象とする。"""

TARGET_PREFECTURES = {"東京都", "神奈川県", "埼玉県", "千葉県"}


def is_in_scope(item: dict) -> bool:
    delivery_type = item.get("delivery_type")
    if delivery_type == "online":
        return True
    if delivery_type == "pickup":
        return item.get("prefecture") in TARGET_PREFECTURES
    return False
