# -*- coding: utf-8 -*-
import csv
import os
import unicodedata

# ここは既存のロジックをそのまま流用してください。
# 重要なのは公開API:
#   - load_dict(csv_path) -> dict
#   - calc(family, given, table) -> dict（下記キー構成）

def load_dict(csv_path: str) -> dict:
    table = {}
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            k = r.get("kanji", "").strip()
            v = r.get("strokes_old", "").strip()
            if not k:
                continue
            try:
                table[k] = int(v)
            except:
                table[k] = 0
    return table

def calc(family: str, given: str, table: dict) -> dict:
    """
    返却する dict は少なくとも下記キーを持つ想定:
        - トップ（天格）: int
        - ハート（人格）: int
        - フット（地格）: int
        - サイド（表面）: int
        - サイド（本質）: int
        - サイド（外格）: int   ← 表示用メイン（仕様に合わせて）
        - オール（総格）  : int
        - breakdown: [(区分, 文字, 画数), ...]
        - _式: {
            "姓": [(文字, 画数), ...],
            "名": [(文字, 画数), ...],
            "トップ": [(文字, 画数), ...],
            "ハート": [(文字, 画数), ...],
            "フット": [(文字, 画数), ...],
            "サイド表面": [(文字, 画数), ...],
            "サイド本質": [(文字, 画数), ...],
            "オール": [(文字, 画数), ...],
        }
    """
    # ----- ここに、すでに作り込まれた正式ロジックをそのまま貼ってください -----
    # 以下はダミー（動作サンプル） — 実運用ではあなたの本ロジックを使う
    def s_of(s):
        return sum(table.get(ch, 0) for ch in s)

    fchars = list(family)
    gchars = list(given)

    top = s_of(family)
    foot = s_of(given)
    heart = (table.get(fchars[-1], 0) if fchars else 0) + (table.get(gchars[0], 0) if gchars else 0)
    side_surface = (table.get(fchars[0], 0) if fchars else 0) + sum(table.get(ch, 0) for ch in gchars[-2:])
    side_essence = (table.get(fchars[0], 0) if fchars else 0) + (table.get(gchars[-1], 0) if gchars else 0)
    side = side_essence  # メイン表示は本質優先など仕様に応じて
    allv = s_of(family) + s_of(given)

    breakdown = []
    for ch in fchars:
        breakdown.append(("姓", ch, table.get(ch, 0)))
    for ch in gchars:
        breakdown.append(("名", ch, table.get(ch, 0)))

    _式 = {
        "姓": [(ch, table.get(ch, 0)) for ch in fchars],
        "名": [(ch, table.get(ch, 0)) for ch in gchars],
        "トップ": [(ch, table.get(ch, 0)) for ch in fchars],
        "ハート": [(fchars[-1], table.get(fchars[-1], 0))] + ([(gchars[0], table.get(gchars[0], 0))] if gchars else [] ) if fchars else [],
        "フット": [(ch, table.get(ch, 0)) for ch in gchars],
        "サイド表面": ([(fchars[0], table.get(fchars[0], 0))] if fchars else []) + [(ch, table.get(ch, 0)) for ch in gchars[-2:]],
        "サイド本質": ([(fchars[0], table.get(fchars[0], 0))] if fchars else []) + ([(gchars[-1], table.get(gchars[-1], 0))] if gchars else []),
        "オール": [(ch, table.get(ch, 0)) for ch in fchars + gchars],
    }

    return {
        "トップ（天格）": top,
        "ハート（人格）": heart,
        "フット（地格）": foot,
        "サイド（表面）": side_surface,
        "サイド（本質）": side_essence,
        "サイド（外格）": side,
        "オール（総格）": allv,
        "breakdown": breakdown,
        "_式": _式,
    }
