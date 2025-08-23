
import argparse, csv, json, time, sys
import urllib.request

API = "https://kanjiapi.dev/v1/kanji/"  # returns JSON, includes "stroke_count"

def fetch_strokes(ch: str) -> int | None:
    url = API + urllib.parse.quote(ch)
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        # Prefer stroke_count; if missing try 'variants' unified field or None
        return int(data.get("stroke_count")) if "stroke_count" in data else None
    except Exception as e:
        return None

def main(path_in: str, path_out: str, delay: float = 0.15):
    # Read CSV
    with open(path_in, "r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    # Ensure required columns
    cols = rows[0].keys() if rows else []
    for col in ["kanji","strokes_old"]:
        if col not in cols:
            print(f"ERROR: CSVに '{col}' 列がありません。", file=sys.stderr)
            sys.exit(1)

    updated = 0
    missing = []
    for r in rows:
        ch = r.get("kanji","").strip()
        cur = str(r.get("strokes_old","")).strip()
        if not ch:
            continue
        if cur and cur.isdigit():
            # すでに数値がある場合は上書きしない（手修正を優先）
            continue
        val = fetch_strokes(ch)
        if val is None:
            missing.append(ch)
        else:
            r["strokes_old"] = str(val)
            updated += 1
        time.sleep(delay)  # APIにやさしく

    # Write out
    with open(path_out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)

    print(f"更新: {updated} 件 / 出力: {path_out}")
    if missing:
        print("未取得（手入力/別ソース要）:", "".join(missing))

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("input_csv", help="元CSV（kanji, strokes_old 列が必要）")
    p.add_argument("--output", default="kanji_master_with_std.csv", help="出力CSVのファイル名")
    p.add_argument("--delay", type=float, default=0.15, help="1件ごとの待機秒（デフォルト0.15）")
    args = p.parse_args()
    main(args.input_csv, args.output, args.delay)
