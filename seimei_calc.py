import argparse
import csv
import sys
import unicodedata
import os

def _load_overrides():
    path = os.path.join(os.path.dirname(__file__), "kanji_overrides.csv")
    data = {}
    try:
        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ch = row.get("char")
                st = row.get("strokes")
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
    "髙": "高",
    "﨑": "崎",
    "邊": "辺",
    "邉": "辺",
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

def calc(family: str, given: str, table: dict):
    f = normalize_name(family)
    g = normalize_name(given)
    fchars = list(f)
    gchars = list(g)

    top = strokes_of(f, table)
    foot = strokes_of(g, table)

    if fchars and gchars:
        heart = stroke_for_char(fchars[-1], table) + stroke_for_char(gchars[0], table)
    else:
        heart = top + foot

    side_head = stroke_for_char(fchars[0], table) if fchars else 0
    side_tail = stroke_for_char(gchars[-1], table) if gchars else 0

    if len(fchars) == 1:
        top += 1
        side_head += 1

    if len(gchars) == 1:
        foot += 1
        side_tail += 1

    allv = strokes_of(f, table) + strokes_of(g, table)

    side = side_head + side_tail

    return {
        "トップ(天格)": top,
        "ハート(人格)": heart,
        "フット(地格)": foot,
        "サイド(外格)": side,
        "オール(総格)": allv,
        "姓(正規化後)": f,
        "名(正規化後)": g,
    }

def main():
    ap = argparse.ArgumentParser(description="姓名の5格を計算（旧字体列を使用）")
    ap.add_argument("csv", help="kanji_master_custom.csv（または kanji_master_with_std.csv）")
    ap.add_argument("--family", "-f", required=True, help="姓（例：田中）")
    ap.add_argument("--given", "-g", required=True, help="名（例：太郎）")
    args = ap.parse_args()

    table = load_dict(args.csv)
    res = calc(args.family, args.given, table)

    print("==== 計算結果 ====")
    print(f"姓：{res['姓(正規化後)']} / 名：{res['名(正規化後)']}")
    for k in ["トップ(天格)", "ハート(人格)", "フット(地格)", "サイド(外格)", "オール(総格)"]:
        print(f"{k}: {res[k]}")

if __name__ == "__main__":
    main()
