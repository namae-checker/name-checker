
import argparse, csv, json, time, sys
import urllib.request, urllib.parse

API = "https://kanjiapi.dev/v1/kanji/"

def fetch_strokes(ch: str):
    url = API + urllib.parse.quote(ch)
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return int(data.get("stroke_count")) if "stroke_count" in data else None
    except Exception as e:
        return None

def main(path_in: str, path_out: str, delay: float = 0.10, verbose: bool = True):
    with open(path_in, "r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    for col in ["kanji","strokes_old"]:
        if col not in rows[0].keys():
            print(f"ERROR: CSVに '{col}' 列がありません。", file=sys.stderr)
            sys.exit(1)

    total = len(rows)
    updated = 0
    missing = []

    for i, r in enumerate(rows, start=1):
        ch = (r.get("kanji") or "").strip()
        cur = (str(r.get("strokes_old") or "")).strip()
        if not ch or (cur.isdigit() and int(cur) > 0):
            if verbose and i % 25 == 0:
                print(f"[{i}/{total}] skip/既存")
            continue

        val = fetch_strokes(ch)
        if val is None:
            missing.append(ch)
        else:
            r["strokes_old"] = str(val)
            updated += 1

        if verbose:
            if val is None:
                print(f"[{i}/{total}] {ch} → 未取得")
            else:
                print(f"[{i}/{total}] {ch} → {val}")

        if delay > 0:
            time.sleep(delay)

    with open(path_out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)

    print(f"更新: {updated} 件 / 出力: {path_out}")
    if missing:
        print("未取得（手入力/別ソース要）:", "".join(missing))

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("input_csv")
    p.add_argument("--output", default="kanji_master_with_std.csv")
    p.add_argument("--delay", type=float, default=0.10)
    p.add_argument("--quiet", action="store_true")
    args = p.parse_args()
    main(args.input_csv, args.output, args.delay, verbose=not args.quiet)
