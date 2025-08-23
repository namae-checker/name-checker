# -*- coding: utf-8 -*-
import argparse
import csv
import os
import unicodedata

def _here(*p):
    return os.path.join(os.path.dirname(__file__), *p)

def _nfkc_strip(s: str) -> str:
    return unicodedata.normalize("NFKC", (s or "")).strip()

# ---------------- dictionary loaders ----------------

def _load_main_dict(csv_path: str) -> dict:
    d = {}
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        # strokes_old / strokes のどちらでも拾えるように
        for r in reader:
            k = _nfkc_strip(r.get("kanji"))
            if not k:
                continue
            v = r.get("strokes_old")
            if v is None:
                v = r.get("strokes")
            v = _nfkc_strip(v)
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
                ch = _nfkc_strip(row.get("char"))
                st = _nfkc_strip(row.get("strokes"))
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
    - radical 名 → 画数
    - aliases（'王|玉|⺩' のような表記）からも同じ画数で引けるようにする
    """
    path = _here("radicals_master.csv")
    d = {}
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                rad = _nfkc_strip(row.get("radical"))
                st  = _nfkc_strip(row.get("strokes_custom"))
                if not rad or not st:
                    continue
                try:
                    val = int(st)
                except Exception:
                    continue
                d[rad] = val
                # エイリアスも登録
                aliases = _nfkc_strip(row.get("aliases"))
                if aliases:
                    for a in aliases.split("|"):
                        a = _nfkc_strip(a)
                        if a and a not in d:
                            d[a] = val
    except FileNotFoundError:
        pass
    return d

def _load_kanji_radicals() -> dict:
    """
    kanji_radicals.csv : (推奨) kanji,radical
                       : 互換   char,radical でも可
    """
    path = _here("kanji_radicals.csv")
    d = {}
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            # ヘッダ名のゆれに対応
            kanji_key = "kanji" if "kanji" in reader.fieldnames else ("char" if "char" in reader.fieldnames else None)
            radical_key = "radical" if "radical" in reader.fieldnames else None
            if not kanji_key or not radical_key:
                return d
            for row in reader:
                ch  = _nfkc_strip(row.get(kanji_key))
                rad = _nfkc_strip(row.get(radical_key))
                if ch and rad:
                    d[ch] = rad
    except FileNotFoundError:
        pass
    return d

# global caches
_KANJI_OVERRIDES = _load_overrides_chars()
_RADICAL_STROKES = _load_radical_strokes()
_KANJI_RADICALS  = _load_kanji_radicals()

# 互換文字 / 繰り返し
VARIANT_MAP = {
    "禎": "祓",
    "琢": "琢",
    "穀": "穀",
    "祝": "祝",
}
REPEAT_MARK = "々"

def normalize_name(s: str) -> str:
    s = unicodedata.normalize("NFKC", s or "")
    out = []
    for ch in s:
        ch = VARIANT_MAP.get(ch, ch)
        if ch == REPEAT_MARK and out:
            ch = out[-1]
        out.append(ch)
    return "".join(out)

# ---------------- strokes ----------------

def stroke_for_char(ch: str, table: dict) -> int:
    # 1) 文字個別オーバーライド
    if ch in _KANJI_OVERRIDES:
        return _KANJI_OVERRIDES[ch]
    # 2) 部首 → 部首画数
    rad = _KANJI_RADICALS.get(ch)
    if rad:
        # radical 名でも alias でも拾える
        st = _RADICAL_STROKES.get(rad)
        if isinstance(st, int):
            return st
    # 3) 通常辞書
    return table.get(ch, 0)

def strokes_of(name: str, table: dict) -> int:
    return sum(stroke_for_char(ch, table) for ch in name)

# ---------------- 5格 ----------------

def calc(family: str, given: str, table: dict):
    f = normalize_name(family)
    g = normalize_name(given)
    fchars = list(f)
    gchars = list(g)

    add_head = 1 if len(fchars) == 1 else 0
    add_tail = 1 if len(gchars) == 1 else 0

    top  = strokes_of(f, table) + add_head
    foot = strokes_of(g, table) + add_tail

    if fchars and gchars:
        heart = stroke_for_char(fchars[-1], table) + stroke_for_char(gchars[0], table)
    else:
        heart = 0

    # 外格：基本は「頭(姓先頭) + ケツ(名末字)」
    side_real = 0
    if fchars:
        side_real += stroke_for_char(fchars[0], table)
    if gchars:
        side_real += stroke_for_char(gchars[-1], table)

    # 3文字名の特例：表面＝頭 + 名の2文字目、本質＝頭 + 名の末字 → 大きい方を採用
    side_face = None
    if len(gchars) >= 2 and fchars:
        side_face = stroke_for_char(fchars[0], table) + stroke_for_char(gchars[1], table)

    side = max(side_real, side_face) if side_face is not None else side_real
    allv = strokes_of(f, table) + strokes_of(g, table)

    return {
        "top": top,
        "heart": heart,
        "foot": foot,
        "side": side,
        "side_face": side_face,
        "side_real": side_real,
        "allv": allv,
    }

# ---------------- CLI ----------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-d", "--dict", required=True, help="kanji_master_xxx.csv")
    ap.add_argument("-f", "--family", default="")
    ap.add_argument("-g", "--given", default="")
    args = ap.parse_args()

    table = _load_main_dict(args.dict)
    res = calc(args.family, args.given, table)
    for k, v in res.items():
        print(k, v)

if __name__ == "__main__":
    main()
