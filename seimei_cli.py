# seimei_cli.py
import csv, unicodedata, os, sys

VARIANT_MAP = {"髙":"高","﨑":"崎","邊":"辺","邉":"辺"}
REPEAT_MARK = "々"

def z2h_digits(s: str) -> str:
    trans = {ord(c): ord('0')+i for i, c in enumerate('０１２３４５６７８９')}
    return s.translate(trans)

def normalize_name(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    out = []
    for ch in s:
        ch = VARIANT_MAP.get(ch, ch)
        if ch == REPEAT_MARK and out:
            ch = out[-1]
        out.append(ch)
    return "".join(out)

def load_table(csv_path: str) -> dict:
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        d = {}
        for row in r:
            k = (row.get("kanji") or "").strip()
            v = (row.get("strokes_old") or "").strip()
            v = z2h_digits(v)
            if not k: continue
            try: d[k] = int(v)
            except: d[k] = 0
        return d

def sum_strokes(s: str, tbl: dict) -> int:
    return sum(tbl.get(ch, 0) for ch in s)

def calc(family: str, given: str, tbl: dict):
    f = normalize_name(family)
    g = normalize_name(given)
    top  = sum_strokes(f, tbl)                      # 天格
    foot = sum_strokes(g, tbl)                      # 地格
    heart = (tbl.get(f[-1],0)+tbl.get(g[0],0)) if (f and g) else (top+foot)  # 人格
    allv = top + foot                               # 総格
    side = max(allv - heart, 0)                     # 外格
    return f,g,top,heart,foot,side,allv

def pick_csv():
    # よく使う3つを候補に
    files = [
        "kanji_master_custom.csv",         # 1
        "kanji_master_joyo.csv",           # 2
        "kanji_master_cultural_affairs.csv" # 3
    ]
    have = [f for f in files if os.path.exists(f)]
    if not have:
        print("CSVが見つかりません。このフォルダにマスタCSVを置いてください。")
        sys.exit(1)
    print("\n== どの辞書を使いますか？ ==")
    for i,f in enumerate(have,1):
        tag = "(カスタム)" if "custom" in f else "(常用)" if "joyo" in f else "(文化庁)"
        print(f"{i}. {f} {tag}")
    while True:
        s = input("番号を入力: ").strip()
        if s.isdigit() and 1 <= int(s) <= len(have):
            return have[int(s)-1]

def main():
    print("=== 姓名5格 計算ツール (CLI) ===")
    csv_path = pick_csv()
    tbl = load_table(csv_path)
    print(f"辞書: {csv_path} / 文字数: {len(tbl)}")

    while True:
        family = input("\n姓（例: 田中／終了=空Enter）: ").strip()
        if not family: break
        given  = input("名（例: 太郎）: ").strip()
        f,g,top,heart,foot,side,allv = calc(family, given, tbl)

        print("\n---- 文字ごとの画数 ----")
        for ch in f: print(f"[姓]{ch} = {tbl.get(ch,0)}")
        for ch in g: print(f"[名]{ch} = {tbl.get(ch,0)}")

        print("\n==== 計算結果 ====")
        print(f"姓：{f} / 名：{g}")
        print(f"トップ(天格): {top}")
        print(f"ハート(人格): {heart}")
        print(f"フット(地格): {foot}")
        print(f"サイド(外格): {side}")
        print(f"オール(総格): {allv}")

if __name__ == "__main__":
    main()
