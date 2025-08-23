# -*- coding: utf-8 -*-
import argparse
import csv
import os
import unicodedata

def _here(*p):
    return os.path.join(os.path.dirname(__file__), *p)

# ---------- loaders ----------
def _load_dict(csv_path: str) -> dict:
    d = {}
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            k = (r.get("kanji") or "").strip()
            v = (r.get("strokes_old") or "").strip()
            if not k:
                continue
            try:
                d[k] = int(v)
            except Exception:
                d[k] = 0
    return d

def _load_overrides_chars() -> dict:
    path = _here("kanji_overrides.csv")
    data = {}
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                ch = (row.get("char") or "").strip()
                st = (row.get("strokes") or "").strip()
                if ch and st:
                    try:
                        data[ch] = int(st)
                    except Exception:
                        pass
    except FileNotFoundError:
        pass
    return data

def _load_radical_strokes() -> dict:
    """
    radicals_master.csv : radical,strokes_custom,aliases
    ここでは radical → strokes_custom だけ使う
    """
    path = _here("radicals_master.csv")
    d = {}
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                rad = (row.get("radical") or "").strip()
                st = (row.get("strokes_custom") or "").strip()
                if not rad:
                    continue
                try:
                    d[rad] = int(st)
                except Exception:
                    pass
    except FileNotFoundError:
        pass
    return d

def _load_kanji_radicals() -> dict:
    """
    kanji_radicals.csv : kanji,radical
    文字 → 部首名 の対応
    """
    path = _here("kanji_radicals.csv")
    d = {}
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                ch = (row.get("kanji") or "").strip()
                rad = (row.get("radical") or "").strip()
                if ch and rad:
                    d[ch] = rad
    except FileNotFoundError:
        pass
    return d

# グローバル・キャッシュ
_KANJI_OVERRIDES = _load_overrides_chars()
_RADICAL_STROKES = _load_radical_strokes()
_KANJI_RADICALS = _load_kanji_radicals()

# 互換の異体字・繰り返し記号
VARIANT_MAP = {
    "禎": "祓",
    "琢": "琢",
    "穀": "穀",
    "祝": "祝",
}
REPEAT_MARK = "々"

def normalize_name(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    out = []
    for ch in s:
        ch = VARIANT_MAP.get(ch, ch)
        if ch == REPEAT_MARK and out:
            ch = out[-1]
        out.append(ch)
    return "".join(out)

# ---------- stroke functions ----------
def stroke_for_char(ch: str, table: dict) -> int:
    # 1) 文字個別オーバーライド
    if ch in _KANJI_OVERRIDES:
        return _KANJI_OVERRIDES[ch]
    # 2) 部首（文字→部首→部首画数）
    rad = _KANJI_RADICALS.get(ch)
    if rad:
        st = _RADICAL_STROKES.get(rad)
        if isinstance(st, int):
            return st
    # 3) 通常辞書
    return table.get(ch, 0)

def strokes_of(name: str, table: dict) -> int:
    return sum(stroke_for_char(ch, table) for ch in name)

# ---------- 5格計算 ----------
def calc(family: str, given: str, table: dict):
    f = normalize_name(family)
    g = normalize_name(given)
    fchars = list(f)
    gchars = list(g)

    # 霊数
    add_head = 1 if len(fchars) == 1 else 0
    add_tail = 1 if len(gchars) == 1 else 0

    # トップ（姓合計 + 頭の霊数）
    top = strokes_of(f, table) + add_head
    # フット（名合計 + ケツの霊数）
    foot = strokes_of(g, table) + add_tail

    # ハート（姓末 + 名頭）
    if fchars and gchars:
        heart = stroke_for_char(fchars[-1], table) + stroke_for_char(gchars[0], table)
    else:
        heart = 0

    # サイド（外格）
    base = 0
    if fchars:
        base += stroke_for_char(fchars[0], table)
    if gchars:
        base += stroke_for_char(gchars[-1], table)

    # 3文字名の特例：表面＝頭+名の2文字目、本質＝頭+名の末字 → 大きい方を採用
    side_face = None
    if len(gchars) >= 2 and fchars:
        side_face = stroke_for_char(fchars[0], table) + stroke_for_char(gchars[1], table)
    side_real = base
    side = max(side_real, side_face) if side_face is not None else side_real

    # 総格（霊数は含めない）
    allv = strokes_of(f, table) + strokes_of(g, table)

    return {
        "top": top,
        "heart": heart,
        "foot": foot,
        "side": side,
        "side_face": side_face,  # 表示用（表面）
        "side_real": side_real,  # 表示用（本質）
        "allv": allv,
    }

# ---------- CLI ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-d", "--dict", required=True, help="kanji_master_xxx.csv")
    ap.add_argument("-f", "--family", default="")
    ap.add_argument("-g", "--given", default="")
    args = ap.parse_args()

    table = _load_dict(args.dict)
    res = calc(args.family, args.given, table)
    for k, v in res.items():
        print(k, v)

if __name__ == "__main__":
    main()
