
import argparse, csv, json, time, urllib.request, urllib.parse, sys

JOYO_URL = "https://kanjiapi.dev/v1/kanji/joyo"
KANJI_URL = "https://kanjiapi.dev/v1/kanji/"  # + <kanji>

def http_get(url, timeout=15):
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return resp.read().decode("utf-8")

def fetch_joyo():
    # returns list[str] of kanji
    data = http_get(JOYO_URL)
    arr = json.loads(data)
    if not isinstance(arr, list): raise RuntimeError("unexpected response for joyo")
    return arr

def fetch_stroke(ch):
    url = KANJI_URL + urllib.parse.quote(ch)
    try:
        data = http_get(url)
        obj = json.loads(data)
        return int(obj.get("stroke_count")) if "stroke_count" in obj else None
    except Exception:
        return None

def main(out_path: str, fill_strokes: bool, delay: float):
    joyo = fetch_joyo()
    print(f"取得: 常用漢字 {len(joyo)} 字")

    rows = []
    missing = []
    done = 0

    for i, ch in enumerate(joyo, start=1):
        stroke = ""
        if fill_strokes:
            val = fetch_stroke(ch)
            if val is None:
                missing.append(ch)
            else:
                stroke = str(val)
            time.sleep(delay)
        rows.append({
            "kanji": ch,
            "strokes_new": "",
            "strokes_old": stroke,
            "element": "",
            "readings": "",
            "notes": ""
        })
        if i % 50 == 0:
            print(f"[{i}/{len(joyo)}] 進行中…")

    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["kanji","strokes_new","strokes_old","element","readings","notes"])
        w.writeheader()
        w.writerows(rows)

    print(f"書き出し: {out_path} / {len(rows)}件")
    if missing:
        print("stroke未取得:", "".join(missing))

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="常用漢字（2136字）から漢字マスタCSVを生成")
    ap.add_argument("--output", default="kanji_master_joyo.csv")
    ap.add_argument("--fill-strokes", action="store_true", help="標準画数も同時取得して strokes_old に入れる")
    ap.add_argument("--delay", type=float, default=0.05, help="API呼び出し間隔秒")
    args = ap.parse_args()
    main(args.output, args.fill_strokes, args.delay)
