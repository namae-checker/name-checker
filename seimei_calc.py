# -*- coding: utf-8 -*-
import argparse
import csv
import sys
import unicodedata
import os

def _load_overrides() -> dict:
    path = os.path.join(os.path.dirname(__file__), "kanji_overrides.csv")
    data = {}
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ch = row.get("char", "").strip()
                st = row.get("strokes", "").strip()
                if ch and st:
                    try:
                        data[ch] = int(st)
                    except ValueError:
                        pass
    except FileNotFoundError:
        pass
    return data

_KANJI_OVERRIDES = _load_overrides()

VARIANT_MAP = {
    "禎": "祓",
    "琢": "琢",
    "穀": "穀",
    "祝": "祝",
}
REPEAT_MARK = "々"

def normalize_name(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    chars = []
    for ch in s:
        ch = VARIANT_MAP.get(ch, ch)
        if ch == REPEAT_MARK and chars:
            ch = chars[-1]
        chars.append(ch)
    return "".join(chars)

def load_dict(csv_path: str) -> dict:
    d = {}
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            k = r.get("kanji", "").strip()
            v = r.get("strokes_old", "").strip()
            if not k:
                continue
            try:
                d[k] = int(v)
            except:
                d[k] = 0
    return d

def stroke_for_char(ch: str, table: dict) -> int:
    if ch in _KANJI_OVERRIDES:
        return _KANJI_OVERRIDES[ch]
    return table.get(ch, 0)

def strokes_of(name: str, table: dict) -> int:
    total = 0
    for ch in name:
        total += stroke_for_char(ch, table)
    return total

def _head_for_side(fchars, table) -> int:
    """
    サイド用『頭』：
      - 姓が1文字のとき…霊数1（頭に1を置く）
      - それ以外 … 姓の先頭字の画数
    """
    if not fchars:
        return 0
    if len(fchars) == 1:
        return 1
    return stroke_for_char(fchars[0], table)

def _tail_for_side(gchars, table) -> int:
    """
    サイド用『ケツ』：
      - 名が1文字のとき…霊数1（ケツに1を置く）
      - それ以外 … 名の末字の画数
    """
    if not gchars:
        return 0
    if len(gchars) == 1:
        return 1
    return stroke_for_char(gchars[-1], table)

def calc(family: str, given: str, table: dict):
    f = normalize_name(family)
    g = normalize_name(given)
    fchars = list(f)
    gchars = list(g)

    # 霊数（総格には含めない）
    add_head = 1 if len(fchars) == 1 else 0   # 姓1文字→頭に+1（トップ/サイド用）
    add_tail = 1 if len(gchars) == 1 else 0   # 名1文字→ケツに+1（フット/サイド用）

    # トップ（天格）…姓の合計 +（姓1文字なら霊数1）
    top = strokes_of(f, table) + add_head

    # フット（地格）…名の合計 +（名1文字なら霊数1）
    foot = strokes_of(g, table) + add_tail

    # ハート（人格）…姓の末字 + 名の先頭字（霊数は含めない）
    if fchars and gchars:
        heart = stroke_for_char(fchars[-1], table) + stroke_for_char(gchars[0], table)
    else:
        heart = 0

    # サイド（外格）
    head_side = _head_for_side(fchars, table)
    tail_side = _tail_for_side(gchars, table)

    # 表面：基本は「頭 + 名の2文字目」。名が1文字のときは「頭 + 1」、
    # 名が2文字のときは「頭 + 名の2文字目」、
    # 名が3文字以上なら「頭 + 名の2文字目」。
    if len(gchars) == 0:
        side_surface = head_side
    elif len(gchars) == 1:
        side_surface = head_side + 1
    else:
        side_surface = head_side + stroke_for_char(gchars[1], table)

    # 本質：常に「頭 + ケツ」。名1文字ならケツ=1
    side_essence = head_side + tail_side

    # 採用値：名が3文字以上のときは max(表面, 本質)、それ以外は本質
    if len(gchars) >= 3:
        side_value = max(side_surface, side_essence)
    else:
        side_value = side_essence

    # オール（総格）…姓＋名の合計（霊数は含めない）
    allv = strokes_of(f, table) + strokes_of(g, table)

    return {
        "トップ（天格）": top,
        "ハート（人格）": heart,
        "フット（地格）": foot,
        "サイド（外格）": side_value,
        "サイド_表面": side_surface,
        "サイド_本質": side_essence,
        "オール（総格）": allv,
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-d", "--dict", required=True, help="kanji_master_xxx.csv")
    ap.add_argument("-f", "--family", default="")
    ap.add_argument("-g", "--given", default="")
    args = ap.parse_args()

    table = load_dict(args.dict)
    res = calc(args.family, args.given, table)
    for k, v in res.items():
        print(f"{k}: {v}")

if __name__ == "__main__":
    main()
