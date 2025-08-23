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
            except Exception:
                d[k] = 0
    return d

def stroke_for_char(ch: str, table: dict) -> int:
    if ch in _KANJI_OVERRIDES:
        return _KANJI_OVERRIDES[ch]
    return table.get(ch, 0)

def strokes_of(name: str, table: dict, breakdown: list, role: str) -> int:
    total = 0
    for ch in name:
        st = stroke_for_char(ch, table)
        breakdown.append((role, ch, st))
        total += st
    return total

def calc(family: str, given: str, table: dict):
    f = normalize_name(family)
    g = normalize_name(given)

    fchars = list(f)
    gchars = list(g)

    add_head = 1 if len(fchars) == 1 else 0
    add_tail = 1 if len(gchars) == 1 else 0

    breakdown = []
    top_base  = strokes_of(f, table, breakdown, role="姓")
    foot_base = strokes_of(g, table, breakdown, role="名")

    # トップ・フット（霊数加味。総格には含めない）
    top  = top_base  + add_head
    foot = foot_base + add_tail

    # ハート
    if fchars and gchars:
        heart = stroke_for_char(fchars[-1], table) + stroke_for_char(gchars[0], table)
    else:
        heart = 0

    # サイド
    side_base = 0
    if fchars:
        side_base += stroke_for_char(fchars[0], table)
    if gchars:
        side_base += stroke_for_char(gchars[-1], table)

    side_surface = side_base   # デフォルト
    side_core    = side_base

    if fchars and len(gchars) >= 2:
        head = stroke_for_char(fchars[0], table)
        second = stroke_for_char(gchars[1], table)
        last = stroke_for_char(gchars[-1], table)
        side_surface = head + second
        side_core    = head + last
        side = max(side_surface, side_core)
    else:
        side = side_base

    # オール（霊数は含めない）
    allv = top_base + foot_base

    return {
        "top": top,
        "heart": heart,
        "foot": foot,
        "side": side,
        "side_surface": side_surface,
        "side_core": side_core,
        "allv": allv,
        "breakdown": breakdown,  # [(役割, 文字, 画数), ...]
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
