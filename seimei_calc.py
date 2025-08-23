import argparse
import csv
import sys
import unicodedata
import os

_DIGITS = {
    "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
    "六": 6, "七": 7, "八": 8, "九": 9, "十": 10
}

def _read_csv(path):
    data = []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            data.append({k: (v if v is not None else "").strip() for k, v in row.items()})
    return data

def _load_table(csv_path):
    d = {}
    if not os.path.exists(csv_path):
        return d
    for r in _read_csv(csv_path):
        k = r.get("kanji", "").strip()
        v = r.get("strokes_old", "").strip()
        if not k or not v:
            continue
        try:
            d[k] = int(v)
        except:
            d[k] = 0
    return d

def _load_kanji_overrides():
    path = os.path.join(os.path.dirname(__file__), "kanji_overrides.csv")
    d = {}
    if not os.path.exists(path):
        return d
    for r in _read_csv(path):
        ch = r.get("char", "").strip()
        v = r.get("strokes", "").strip()
        if ch and v:
            try:
                d[ch] = int(v)
            except:
                pass
    return d

def _load_radicals():
    path = os.path.join(os.path.dirname(__file__), "radicals_master.csv")
    d = {}
    if not os.path.exists(path):
        return d
    for r in _read_csv(path):
        rad = r.get("radical", "").strip()
        v = r.get("strokes_custom", "").strip()
        if rad and v:
            try:
                d[rad] = int(v)
            except:
                pass
        aliases = r.get("aliases", "").strip()
        if aliases:
            for al in [a.strip() for a in aliases.split("|") if a.strip()]:
                try:
                    d[al] = int(v)
                except:
                    pass
    return d

def _load_radical_overrides():
    path = os.path.join(os.path.dirname(__file__), "radical_overrides.csv")
    d = {}
    if not os.path.exists(path):
        return d
    for r in _read_csv(path):
        ch = r.get("char", "").strip()
        rad = r.get("radical", "").strip()
        if ch and rad:
            d[ch] = rad
    return d

_VARIANT_MAP = {
    "髙": "高",
    "﨑": "崎",
    "邉": "辺",
    "邊": "辺",
}
_REPEAT = "々"

def normalize_name(s):
    s = unicodedata.normalize("NFKC", s or "")
    out = []
    for ch in s:
        ch = _VARIANT_MAP.get(ch, ch)
        if ch == _REPEAT and out:
            ch = out[-1]
        out.append(ch)
    return "".join(out)

def stroke_for_char(ch, table, k_ovr, rad_map, rad_ovr):
    if ch in _DIGITS:
        return _DIGITS[ch]
    if ch in k_ovr:
        return k_ovr[ch]
    if ch in rad_ovr:
        rad = rad_ovr[ch]
        if rad in rad_map:
            return rad_map[rad]
    return table.get(ch, 0)

def strokes_of(name, table):
    total = 0
    k_ovr = _load_kanji_overrides()
    rad_map = _load_radicals()
    rad_ovr = _load_radical_overrides()
    for ch in name:
        total += stroke_for_char(ch, table, k_ovr, rad_map, rad_ovr)
    return total

def stroke_first_char(name, table):
    if not name:
        return 0
    k_ovr = _load_kanji_overrides()
    rad_map = _load_radicals()
    rad_ovr = _load_radical_overrides()
    return stroke_for_char(name[0], table, k_ovr, rad_map, rad_ovr)

def stroke_last_char(name, table):
    if not name:
        return 0
    k_ovr = _load_kanji_overrides()
    rad_map = _load_radicals()
    rad_ovr = _load_radical_overrides()
    return stroke_for_char(name[-1], table, k_ovr, rad_map, rad_ovr)

def calc(family, given, table):
    f = normalize_name(family)
    g = normalize_name(given)

    top = strokes_of(f, table)
    foot = strokes_of(g, table)

    heart = 0
    if f and g:
        heart = stroke_last_char(f, table) + stroke_first_char(g, table)

    side_pair = stroke_first_char(f, table) + stroke_last_char(g, table)
    side = side_pair

    add_head = 1 if len(f) == 1 else 0
    add_tail = 1 if len(g) == 1 else 0

    top_side = top + add_head
    foot_side = foot + add_tail

    allv = top + foot

    return {
        "トップ(天格)": top_side,
        "ハート(人格)": heart,
        "フット(地格)": foot_side,
        "サイド(外格)": max(top_side - heart, side, foot_side - heart),
        "オール(総格)": allv,
        "詳細": {
            "姓": f,
            "名": g,
            "姓末": stroke_last_char(f, table),
            "名頭": stroke_first_char(g, table),
            "姓頭": stroke_first_char(f, table),
            "名末": stroke_last_char(g, table),
            "霊数姓": add_head,
            "霊数名": add_tail
        }
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", default="kanji_master_joyo.csv")
    ap.add_argument("-f", "--family", default="")
    ap.add_argument("-g", "--given", default="")
    args = ap.parse_args()
    table = _load_table(args.table)
    res = calc(args.family, args.given, table)
    for k, v in res.items():
        if k == "詳細":
            continue
        print(f"{k}: {v}")

if __name__ == "__main__":
    main()
