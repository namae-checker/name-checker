# -*- coding: utf-8 -*-
import csv
import os
import unicodedata
from typing import Dict, List, Tuple

# ====== 設定 ======
DICT_FILE = "kanji_master_joyo.csv"     # 常にこの辞書を使用
OVERRIDES_FILE = "kanji_overrides.csv"  # 存在すれば優先適用

REPEAT_MARK = "々"
VARIANT_MAP = {
    # 必要に応じて異体字→正字体に正規化
    "禎": "祓",
    "琢": "琢",
    "穀": "穀",
    "祝": "祝",
}

# ====== ローダ ======
def _load_overrides() -> Dict[str, int]:
    path = os.path.join(os.path.dirname(__file__), OVERRIDES_FILE)
    data = {}
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            rdr = csv.DictReader(f)
            for row in rdr:
                ch = (row.get("char") or "").strip()
                v  = (row.get("strokes") or "").strip()
                if ch and v:
                    try:
                        data[ch] = int(v)
                    except ValueError:
                        pass
    except FileNotFoundError:
        pass
    return data

def load_dict() -> Dict[str, int]:
    """kanji_master_joyo.csv を固定で読み込む"""
    path = os.path.join(os.path.dirname(__file__), DICT_FILE)
    d = {}
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        rdr = csv.DictReader(f)
        # 既存辞書カラム例: kanji, strokes_old など
        # プロジェクトのCSVに合わせて主要カラム名を抽出する
        # 優先: strokes_old / strokes / count の順で探索
        header = [c.strip().lower() for c in rdr.fieldnames or []]
        if "kanji" not in header:
            raise RuntimeError("CSVに 'kanji' 列が見つかりません: " + DICT_FILE)

        def pick(row, *cands):
            for c in cands:
                if c in row and (row[c] or "").strip():
                    return (row[c] or "").strip()
            return ""

        for row in rdr:
            r = {k.strip().lower(): (v or "").strip() for k, v in row.items()}
            k = r.get("kanji", "")
            if not k:
                continue
            v_str = pick(r, "strokes_old", "strokes", "count")
            try:
                d[k] = int(v_str)
            except ValueError:
                d[k] = 0
    return d

_KANJI_OVERRIDES = _load_overrides()


# ====== 正規化 & 画数 ======
def normalize_name(s: str) -> str:
    s = unicodedata.normalize("NFKC", s or "")
    out: List[str] = []
    for ch in s:
        ch = VARIANT_MAP.get(ch, ch)
        if ch == REPEAT_MARK and out:
            ch = out[-1]
        out.append(ch)
    return "".join(out)

def stroke_for_char(ch: str, table: Dict[str, int]) -> int:
    if ch in _KANJI_OVERRIDES:
        return _KANJI_OVERRIDES[ch]
    return table.get(ch, 0)

def strokes_of(name: str, table: Dict[str, int]) -> int:
    total = 0
    for ch in name:
        total += stroke_for_char(ch, table)
    return total


# ====== サイド計算のユーティリティ ======
def _sum_first(chars: List[str], n: int, table: Dict[str, int]) -> int:
    return sum(stroke_for_char(c, table) for c in chars[:n])

def _sum_last(chars: List[str], n: int, table: Dict[str, int]) -> int:
    return sum(stroke_for_char(c, table) for c in chars[-n:]) if n > 0 else 0


def calc(
    family: str,
    given: str,
    table: Dict[str, int],
) -> Dict[str, int | str | List[Tuple[str, int, str]]]:
    """
    ルール（ユーザー定義）に従って 5数を算出する:
    - 霊数は総画(オール)に含めない
    - 霊数の付与位置:
        姓が1文字 → 頭に+1
        名が1文字 → ケツに+1
    - サイド:
        4) 名が3文字以上 → 表面: 姓1 + 名末2, 本質: 姓1 + 名末1
           例外) 姓・名ともに3文字以上 → サイド = 姓頭2 + 名末2（表面=本質）
        5) 姓が3文字以上 → サイド = 姓頭2 + 名末1（表面=本質）
        付記) 姓1文字＋名3文字 → サイド: 表面=霊数1 + 名末2 / 本質=霊数1 + 名末1
        付記) 名1文字 → ケツ霊数をサイドにも反映（姓1=霊、名1=霊の合算）
    - 総画 > 60 は 1 からカウントし直し (61→1, 62→2, ...)
    """

    f = normalize_name(family)
    g = normalize_name(given)
    fchars = list(f)
    gchars = list(g)
    fn, gn = len(fchars), len(gchars)

    # 霊数の付与
    rei_head = 1 if fn == 1 else 0
    rei_tail = 1 if gn == 1 else 0

    # トップ（天格）
    top = strokes_of(f, table) + rei_head

    # ハート（人格）
    heart = 0
    if fn > 0 and gn > 0:
        heart = stroke_for_char(fchars[-1], table) + stroke_for_char(gchars[0], table)

    # フット（地格）
    foot = strokes_of(g, table) + rei_tail

    # サイド（外格）: 表面/本質の両方を可能なら計算
    side_surface = None
    side_essence = None

    # 例外：姓・名ともに3文字以上 → サイド=姓頭2+名末2（表面=本質）
    if fn >= 3 and gn >= 3:
        v = _sum_first(fchars, 2, table) + _sum_last(gchars, 2, table)
        side_essence = side_surface = v

    # 姓が3文字以上 → サイド=姓頭2+名末1（表面=本質）
    elif fn >= 3 and gn >= 1:
        v = _sum_first(fchars, 2, table) + _sum_last(gchars, 1, table)
        # 名1文字ならケツ霊数も乗る
        if gn == 1:
            v += rei_tail
        side_essence = side_surface = v

    else:
        # それ以外の基本（名が3文字以上なら 表面/本質）
        # 表面: 姓1 + 名末2／本質: 姓1 + 名末1
        # 姓1文字の場合は頭は霊数1
        head_1 = rei_head if fn == 1 else (_sum_first(fchars, 1, table) if fn >= 1 else 0)

        if gn >= 3:
            tail_1 = _sum_last(gchars, 1, table)
            tail_2 = _sum_last(gchars, 2, table)
            # 名1文字のケースはここに来ないが、念のため
            side_essence = head_1 + tail_1
            side_surface = head_1 + tail_2

        elif gn == 2:
            tail_1 = _sum_last(gchars, 1, table)
            side_essence = head_1 + tail_1
            side_surface = side_essence  # 表面は定義なし→同値扱い

        elif gn == 1:
            tail_1 = _sum_last(gchars, 1, table)
            side_essence = head_1 + tail_1 + rei_tail  # ケツ霊数も乗る
            side_surface = side_essence

        else:
            side_essence = head_1
            side_surface = head_1

    # 総画（オール）は霊数を含めない
    allv_raw = strokes_of(f, table) + strokes_of(g, table)
    # 60 超過なら 1 から数え直し（61→1）
    allv = ((allv_raw - 1) % 60) + 1 if allv_raw > 60 else allv_raw

    # 文字内訳（霊数は別途表記）
    breakdown: List[Tuple[str, int, str]] = []
    for ch in fchars:
        breakdown.append(("姓", stroke_for_char(ch, table), ch))
    for ch in gchars:
        breakdown.append(("名", stroke_for_char(ch, table), ch))
    # 霊数の見える化（集計に含めない）
    if rei_head:
        breakdown.append(("霊", 1, "頭"))
    if rei_tail:
        breakdown.append(("霊", 1, "末"))

    return {
        "トップ（天格）": top,
        "ハート（人格）": heart,
        "フット（地格）": foot,
        "サイド": max(side_essence, 0),
        "サイド（表面）": side_surface,
        "サイド（本質）": side_essence,
        "オール（総格）": allv,
        "内訳": breakdown,
    }
