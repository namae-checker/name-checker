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
            for row in csv.DictReader(f):
                ch = (row.get("char") or "").strip()
                st = (row.get("strokes") or "").strip()
                if ch and st:
                    try:
                        data[ch] = int(st)
                    except ValueError:
                        pass
    except FileNotFoundError:
        pass
    return data

_KANJI_OVERRIDES = _load_overrides()

# 追加：radicals_master.csv を読み込む（aliases を '|' で分割）
def load_radicals_master(path: str) -> list[dict]:
    """
    radicals_master.csv
      - header: radical,strokes_custom,aliases
      - aliases: '王|玉|玊' のように '|' 区切り
    """
    items = []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            radical = (r.get("radical") or "").strip()
            st_str  = (r.get("strokes_custom") or "").strip()
            al_raw  = (r.get("aliases") or "").strip()
            if not radical or not st_str:
                continue
            try:
                st = int(st_str)
            except ValueError:
                continue
            aliases = [a.strip() for a in al_raw.split("|") if a.strip()]
            items.append({"radical": radical, "strokes": st, "aliases": aliases})
    return items

# 追加：kanji_radicals.csv を読み込む（char->radical 自体 or 代表字 など）
def load_kanji_radicals(path: str) -> dict:
    """
    kanji_radicals.csv
      - header: char,radical
      - 例: '理,王'
    """
    d = {}
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            ch = (r.get("char") or "").strip()
            ra = (r.get("radical") or "").strip()
            if ch and ra:
                d[ch] = ra
    return d

# 既存：異体字・々の展開
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

# 既存：漢字辞書（常用など）
def load_dict(csv_path: str) -> dict:
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

# 追加：部首 → strokes を引くための逆引きテーブル（alias -> strokes）
def build_alias_to_strokes(rad_master: list[dict]) -> dict:
    alias2st = {}
    for item in rad_master:
        st = item["strokes"]
        for a in item["aliases"]:
            alias2st[a] = st
    return alias2st

# 文字1コの画数決定：オーバーライド > 部首指定 > 辞書
def stroke_for_char(ch: str, table: dict,
                    kr_map: dict | None = None,
                    alias2st: dict | None = None) -> int:
    # ① 文字単位のオーバーライド最優先
    if ch in _KANJI_OVERRIDES:
        return _KANJI_OVERRIDES[ch]

    # ② 部首指定があれば（kanji_radicals.csv -> alias を strokes に）
    if kr_map and alias2st:
        alias = kr_map.get(ch)
        if alias:
            alias = alias.strip()
            # 例: '王' を '王|玉|玊' の各要素に分割済み dict で引く
            if alias in alias2st:
                return alias2st[alias]

    # ③ 通常辞書
    return table.get(ch, 0)

def strokes_of(name: str, table: dict,
               kr_map: dict | None = None,
               alias2st: dict | None = None) -> int:
    return sum(stroke_for_char(ch, table, kr_map, alias2st) for ch in name)

def calc(family: str, given: str, table: dict,
         kr_map: dict | None = None,
         alias2st: dict | None = None):
    f = normalize_name(family)
    g = normalize_name(given)
    fchars = list(f)
    gchars = list(g)

    # 霊数ルール
    add_head = 1 if len(fchars) == 1 else 0  # 姓1文字→頭+1（総格除外）
    add_tail = 1 if len(gchars) == 1 else 0  # 名1文字→ケツ+1（総格除外）

    top  = strokes_of(f, table, kr_map, alias2st) + add_head
    foot = strokes_of(g, table, kr_map, alias2st) + add_tail

    heart = 0
    if fchars and gchars:
        heart = (
            stroke_for_char(fchars[-1], table, kr_map, alias2st) +
            stroke_for_char(gchars[0],  table, kr_map, alias2st)
        )

    # サイド（外格）：基本=頭(姓先頭)+ケツ(名末字)
    side_face = 0
    if fchars:
        side_face += stroke_for_char(fchars[0], table, kr_map, alias2st)
    if gchars:
        side_face += stroke_for_char(gchars[-1], table, kr_map, alias2st)

    # 3文字名は 表面=頭+名2文字目 / 本質=頭+名末字 → 最大値と内訳
    if len(gchars) >= 2 and fchars:
        side_core = (
            stroke_for_char(fchars[0], table, kr_map, alias2st) +
            stroke_for_char(gchars[-1], table, kr_map, alias2st)
        )
        side = max(side_face, side_core)
        side_alt = {"face": side_face, "core": side_core}
    else:
        side = side_face
        side_alt = {"face": side_face, "core": side_face}

    allv = strokes_of(f, table, kr_map, alias2st) + strokes_of(g, table, kr_map, alias2st)

    return {
        "top": top,
        "heart": heart,
        "foot": foot,
        "side": side,
        "side_alt": side_alt,  # 表示用：(表面=, 本質=)
        "allv": allv,
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-d", "--dict", required=True)
    ap.add_argument("--radicals-master", default="radicals_master.csv")
    ap.add_argument("--kanji-radicals",  default="kanji_radicals.csv")
    ap.add_argument("-f", "--family", default="")
    ap.add_argument("-g", "--given",  default="")
    args = ap.parse_args()

    table = load_dict(args.dict)

    # 部首系の読み込み
    rad_master = load_radicals_master(args.radicals_master)
    alias2st   = build_alias_to_strokes(rad_master)
    try:
        kr_map = load_kanji_radicals(args.kanji_radicals)
    except FileNotFoundError:
        kr_map = {}

    res = calc(args.family, args.given, table, kr_map, alias2st)
    for k, v in res.items():
        print(k, v)

if __name__ == "__main__":
    main()
