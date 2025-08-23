import argparse, json, pandas as pd

# 入力CSV: kanji, strokes_old, strokes_new, element, readings, notes
# ルールJSONの例:
# {
#   "version": "radical-offset-v1",
#   "relative_groups": [
#     {"offset": +1, "chars": "辶之⻌込近返迎…"},
#     {"offset": -1, "chars": "阝部附院階際際…"}
#   ],
#   "absolute_overrides": {
#     "辻": 6,
#     "崎": 11
#   }
# }
#
# 適用順序:
# 1) 基本値 = strokes_old（空なら 0）
# 2) relative_groups を順に足し合わせ
# 3) absolute_overrides があれば最終値をその値に置換
#
# 使い方例:
# python apply_stroke_overrides.py input.csv rules.json --output output.csv

def main(input_csv: str, rules_json: str, output_csv: str):
    df = pd.read_csv(input_csv, dtype={"kanji": str})
    with open(rules_json, "r", encoding="utf-8") as f:
        rules = json.load(f)

    # strokes_old を数値化（空欄は0）
    def to_int(x):
        try:
            return int(x)
        except:
            return 0

    df["strokes_old"] = df["strokes_old"].apply(to_int)
    base = df["strokes_old"].copy()

    # 相対オフセット適用
    for grp in rules.get("relative_groups", []):
        offset = int(grp.get("offset", 0))
        chars = set(list(grp.get("chars", "")))
        mask = df["kanji"].apply(lambda k: k in chars)
        df.loc[mask, "strokes_old"] = df.loc[mask, "strokes_old"] + offset

    # 絶対オーバーライド適用
    abs_map = rules.get("absolute_overrides", {})
    if abs_map:
        # 文字列キーなので辞書として直接参照
        df["strokes_old"] = df.apply(
            lambda r: int(abs_map.get(str(r["kanji"]), r["strokes_old"])),
            axis=1
        )

    # notes に適用情報を追記
    note_col = "notes" if "notes" in df.columns else None
    if note_col:
        tag = f'[{rules.get("version","custom")}]'
        df["notes"] = df["notes"].fillna("")
        df.loc[df["strokes_old"] != base, "notes"] = (
            df.loc[df["strokes_old"] != base, "notes"].astype(str).str.rstrip()
            + ("" if df.loc[df["strokes_old"] != base, "notes"].eq("").all() else " ")
            + tag
        )

    df.to_csv(output_csv, index=False, encoding="utf-8-sig")
    print(f"書き出し: {output_csv} / {len(df)}件")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("input_csv")
    ap.add_argument("rules_json")
    ap.add_argument("--output", default="output.csv")
    args = ap.parse_args()
    main(args.input_csv, args.rules_json, args.output)
