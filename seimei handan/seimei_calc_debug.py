import argparse, csv, unicodedata

VARIANT_MAP = {"髙":"高","﨑":"崎","邊":"辺","邉":"辺"}
REPEAT_MARK = "々"

def z2h_digits(s: str) -> str:
    trans = {ord(c): ord('0')+i for i, c in enumerate('０１２３４５６７８９')}
    s = s.translate(trans)
    return "".join(ch for ch in s if ch.isdigit() or ch in "+-")

def normalize_name(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    out = []
    for ch in s:
        ch = VARIANT_MAP.get(ch, ch)
        if ch == REPEAT_MARK and out:
            ch = out[-1]
        out.append(ch)
    return "".join(out)

def load_table(path: str) -> dict:
    table = {}
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        headers = [h.strip() for h in reader.fieldnames or []]
        try:
            idx_k = headers.index("kanji")
            idx_s = headers.index("strokes_old")
        except ValueError:
            raise SystemExit("CSVの列名に 'kanji' または 'strokes_old' がありません。")
        for r in reader:
            k = (r.get("kanji") or r[headers[idx_k]] or "").strip()
            vraw = (r.get("strokes_old") or r[headers[idx_s]] or "").strip()
            vraw = z2h_digits(vraw)
            if not k:
                continue
            try:
                v = int(vraw) if vraw != "" else 0
            except Exception:
                v = 0
            table[k] = v
    return table

def sum_strokes(s: str, tbl: dict) -> int:
    return sum(tbl.get(ch, 0) for ch in s)

def main():
    ap = argparse.ArgumentParser(description="5格計算（デバッグ表示つき）")
    ap.add_argument("csv", help="kanji_master_custom.csv")
    ap.add_argument("--family", "-f", required=True)
    ap.add_argument("--given", "-g", required=True)
    ap.add_argument("--verbose", "-v", action="store_true", help="各文字の画数を表示")
    args = ap.parse_args()

    tbl = load_table(args.csv)
    fam = normalize_name(args.family)
    giv = normalize_name(args.given)

    if args.verbose:
        print("---- 文字ごとの画数 ----")
        for ch in fam:
            print(f"[姓]{ch} = {tbl.get(ch, 0)}")
        for ch in giv:
            print(f"[名]{ch} = {tbl.get(ch, 0)}")

    top = sum_strokes(fam, tbl)
    foot = sum_strokes(giv, tbl)
    heart = (tbl.get(fam[-1],0) + tbl.get(giv[0],0)) if (fam and giv) else top+foot
    allv = top + foot
    side = max(allv - heart, 0)

    print("\n==== 計算結果 ====")
    print(f"姓：{fam} / 名：{giv}")
    print(f"トップ(天格): {top}")
    print(f"ハート(人格): {heart}")
    print(f"フット(地格): {foot}")
    print(f"サイド(外格): {side}")
    print(f"オール(総格): {allv}")

if __name__ == "__main__":
    main()
