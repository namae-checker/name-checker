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
    # ① 文字単位のオーバーライドが最優先
    if ch in _KANJI_OVERRIDES:
        return _KANJI_OVERRIDES[ch]
    # ② 辞書の画数
    return table.get(ch, 0)

def strokes_of(name: str, table: dict) -> int:
    total = 0
    for ch in name:
        total += stroke_for_char(ch, table)
    return total

def calc(family: str, given: str, table: dict):
    f = normalize_name(family)
    g = normalize_name(given)

    fchars = list(f)
    gchars = list(g)

    # 霊数ルール
    add_head = 1 if len(fchars) == 1 else 0  # 姓が1文字→頭に +1（総格へは含めない）
    add_tail = 1 if len(gchars) == 1 else 0  # 名が1文字→ケツに +1（総格へは含めない）

    # トップ（天格）…姓の合計 + 霊数(頭)
    top = strokes_of(f, table) + add_head

    # フット（地格）…名の合計 + 霊数(ケツ)
    foot = strokes_of(g, table) + add_tail

    # ハート（人格）…姓の末字 + 名の先頭字
    if fchars and gchars:
        heart = stroke_for_char(fchars[-1], table) + stroke_for_char(gchars[0], table)
    else:
        heart = 0

    # サイド（外格）
    # 基本：頭（姓の先頭）とケツ（名の末字）の和。
    side_base = 0
    if fchars:
        side_base += stroke_for_char(fchars[0], table)
    if gchars:
        side_base += stroke_for_char(gchars[-1], table)
    # 3文字名の例外（「木原 由香里」型）：表面=頭+名の2文字目, 本質=頭+名の末字 → 最大値を採用
    if len(gchars) >= 2:
        side_alt = 0
        if fchars:
            side_alt += stroke_for_char(fchars[0], table)
        side_alt += stroke_for_char(gchars[-1], table)
        side = max(side_base, side_alt)
    else:
        side = side_base

    # オール（総格）…姓＋名の合計。霊数は含めない
    allv = strokes_of(f, table) + strokes_of(g, table)

    return {
        "トップ（天格）": top,
        "ハート（人格）": heart,
        "フット（地格）": foot,
        "サイド（外格）": side,
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
