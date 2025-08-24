# -*- coding: utf-8 -*-
import argparse
import csv
import os
import sys
import unicodedata
from typing import Dict, List, Tuple, Optional

# -----------------------------
# 文字個別オーバーライド（最優先）
# -----------------------------
def _load_overrides() -> Dict[str, int]:
    path = os.path.join(os.path.dirname(__file__), "kanji_overrides.csv")
    data: Dict[str, int] = {}
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
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

_KANJI_OVERRIDES: Dict[str, int] = _load_overrides()

# -----------------------------
# 表記ゆれ吸収
# -----------------------------
VARIANT_MAP = {
    "禎": "祓",
    "琢": "琢",
    "穀": "穀",
    "祝": "祝",
}
REPEAT_MARK = "々"

def normalize_name(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    out: List[str] = []
    for ch in s:
        ch = VARIANT_MAP.get(ch, ch)
        if ch == REPEAT_MARK and out:
            ch = out[-1]
        out.append(ch)
    return "".join(out)

# -----------------------------
# 辞書読み込み（kanji, strokes_old）
# -----------------------------
def load_dict(csv_path: str) -> Dict[str, int]:
    d: Dict[str, int] = {}
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

# -----------------------------
# 画数取得
# -----------------------------
def stroke_for_char(ch: str, table: Dict[str, int]) -> int:
    if ch in _KANJI_OVERRIDES:
        return _KANJI_OVERRIDES[ch]
    return table.get(ch, 0)

def strokes_sum(chars: List[str], table: Dict[str, int]) -> int:
    return sum(stroke_for_char(c, table) for c in chars)

# -----------------------------
# サイド（外格）計算：表面/本質
# ルール（最終）に対応：
#  - 名が3文字以上：表面=頭1 + 末尾2、 本質=頭1 + 末尾1
#  - ただし 例外：姓/名とも3文字以上 → サイド=頭2 + 末尾2（単一値）
#  - 姓が3文字以上：サイド=頭2 + 末尾1
#  - 名が1文字：末尾は霊数1を用いる
#  - 姓が1文字：頭は霊数1を用いる
# -----------------------------
def _side_values(
    fchars: List[str],
    gchars: List[str],
    table: Dict[str, int],
    reisu_head: int,
    reisu_tail: int,
) -> Tuple[int, Optional[int]]:
    lf = len(fchars)
    lg = len(gchars)

    def head1() -> int:
        # 姓が1文字 → 霊数1、そうでなければ姓先頭の画数
        if lf == 0:
            return 0
        return reisu_head if lf == 1 else stroke_for_char(fchars[0], table)

    def head2() -> int:
        # 頭2文字（呼ばれるのは lf >= 3 の条件下）
        return stroke_for_char(fchars[0], table) + stroke_for_char(fchars[1], table)

    def tail1() -> int:
        # 名の末尾1文字。名1文字のときは霊数1を使う。
        if lg == 0:
            return 0
        if lg == 1:
            return reisu_tail
        return stroke_for_char(gchars[-1], table)

    def tail2_sum() -> int:
        # 名の末尾2文字（呼ばれるのは lg >= 3 の条件下）
        return stroke_for_char(gchars[-2], table) + stroke_for_char(gchars[-1], table)

    # 例外：姓・名ともに3文字以上 → サイドは「頭2 + 末尾2」の単一値
    if lf >= 3 and lg >= 3:
        side = head2() + tail2_sum()
        return side, None

    # 姓が3文字以上 → サイドは「頭2 + 末尾1」
    if lf >= 3:
        side = head2() + tail1()
        return side, None

    # 名が3文字以上（姓は1 or 2）
    if lg >= 3:
        h = head1()
        essential = h + tail1()           # 本質：頭1 + 末尾1
        surface   = h + tail2_sum()       # 表面：頭1 + 末尾2
        return essential, surface

    # それ以外（名が2文字以下）
    #   - 名1文字なら末尾=霊数1
    #   - 姓1文字なら頭=霊数1
    side = head1() + tail1()
    return side, None

# -----------------------------
# 総格の 60 超リセット（>60 のとき再び 1 から）
# 例：63 → 3、 60 は 60 のまま
# -----------------------------
def wrap60(total: int) -> int:
    if total > 60:
        # 61→1, 62→2, ... 120→60
        return ((total - 1) % 60) + 1
    return total

# -----------------------------
# 5格メイン計算
# -----------------------------
def calc(family: str, given: str, table: Dict[str, int]) -> Dict[str, int]:
    f = normalize_name(family)
    g = normalize_name(given)
    fchars = list(f)
    gchars = list(g)
    lf, lg = len(fchars), len(gchars)

    # 霊数（総格/人格には入れない）
    reisu_head = 1 if lf == 1 else 0  # 姓1文字→頭に1
    reisu_tail = 1 if lg == 1 else 0  # 名1文字→末尾に1

    # トップ（天格）
    top = strokes_sum(fchars, table) + reisu_head

    # ハート（人格）…姓末字 + 名先頭（霊数なし）
    if lf > 0 and lg > 0:
        heart = stroke_for_char(fchars[-1], table) + stroke_for_char(gchars[0], table)
    else:
        heart = 0

    # フット（地格）
    foot = strokes_sum(gchars, table) + reisu_tail

    # サイド（外格）
    side_essential, side_surface = _side_values(fchars, gchars, table, reisu_head, reisu_tail)

    # オール（総格）…霊数なし → 60超は再カウント
    all_total = strokes_sum(fchars, table) + strokes_sum(gchars, table)
    allv = wrap60(all_total)

    res: Dict[str, int] = {
        "トップ（天格）": top,
        "ハート（人格）": heart,
        "フット（地格）": foot,
        "サイド（外格・本質）": side_essential,
        "オール（総格）": allv,
    }
    if side_surface is not None:
        res["サイド（外格・表面）"] = side_surface
    return res

# -----------------------------
# CLI（任意）
# -----------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-d", "--dict", required=True, help="kanji_master_xxx.csv")
    ap.add_argument("-f", "--family", default="")
    ap.add_argument("-g", "--given", default="")
    args = ap.parse_args()

    table = load_dict(args.dict)
    out = calc(args.family, args.given, table)
    for k, v in out.items():
        print(f"{k}: {v}")

if __name__ == "__main__":
    main()
