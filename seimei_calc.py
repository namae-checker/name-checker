# -*- coding: utf-8 -*-
"""
姓名判断 計算ロジック（完全版）
- 固定辞書: kanji_master_joyo.csv を読み込む
- 追加上書き: kanji_overrides.csv があれば優先（char,strokes）
- 霊数の扱い / サイド（表面・本質） / 総格>60 の折り返し / 数式文字列 を返す
"""

import csv
import os
import unicodedata

# 変体・互換などの最小正規化と、繰り返し記号の展開
VARIANT_MAP = {
    "禎": "祓",
    "琢": "琢",
    "穀": "穀",
    "祝": "祝",
}
REPEAT_MARK = "々"


def _here(*p):
    return os.path.join(os.path.dirname(__file__), *p)


def normalize_name(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    out = []
    for ch in s:
        ch = VARIANT_MAP.get(ch, ch)
        if ch == REPEAT_MARK and out:
            ch = out[-1]
        out.append(ch)
    return "".join(out)


def load_base_dict() -> dict[str, int]:
    """
    kanji_master_joyo.csv を読み込む
    期待カラム: kanji, strokes_old（無ければ strokes なども探索）
    """
    path = _here("kanji_master_joyo.csv")
    d: dict[str, int] = {}
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames or []
        # カラム名の候補
        k_col = "kanji" if "kanji" in cols else cols[0]
        s_col = "strokes_old" if "strokes_old" in cols else ("strokes" if "strokes" in cols else cols[1])
        for r in reader:
            ch = (r.get(k_col) or "").strip()
            v = (r.get(s_col) or "").strip()
            if not ch:
                continue
            try:
                d[ch] = int(v)
            except Exception:
                d[ch] = 0
    return d


def load_overrides() -> dict[str, int]:
    """
    kanji_overrides.csv があれば優先する
    期待カラム: char, strokes
    """
    path = _here("kanji_overrides.csv")
    if not os.path.exists(path):
        return {}
    d: dict[str, int] = {}
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            ch = (r.get("char") or "").strip()
            st = (r.get("strokes") or "").strip()
            if ch and st:
                try:
                    d[ch] = int(st)
                except Exception:
                    pass
    return d


class StrokeTable:
    def __init__(self):
        self.base = load_base_dict()
        self.over = load_overrides()

    def stroke(self, ch: str) -> int:
        if ch in self.over:
            return self.over[ch]
        return self.base.get(ch, 0)


def _labels(chars: list[str], tbl: StrokeTable) -> list[str]:
    return [f"{ch}({tbl.stroke(ch)})" for ch in chars]


def _sum_strokes(chars: list[str], tbl: StrokeTable) -> int:
    return sum(tbl.stroke(ch) for ch in chars)


def _wrap60(x: int) -> int:
    """総格が60を超えた場合 1〜60 に折り返す"""
    if x <= 60:
        return x
    # 1..60 の巡回
    return ((x - 1) % 60) + 1


def _side_values(fchars: list[str], gchars: list[str], tbl: StrokeTable):
    """
    サイドの「表面」「本質」「主表示値」をルール通りに計算。
    ルール（要旨）:
      - 本質: 頭=姓1文字目（姓1文字なら霊1） + ケツ=名末尾（名1文字なら霊1）
      - 表面: 頭=姓1文字目（姓1文字なら霊1） + 名末尾2文字（名が2未満ならあるだけ / 名1文字なら霊1を足す）
      - 例外:
          * 姓3文字以上かつ名3文字以上 → 主表示 = 姓頭2 + 名末尾2
          * 姓3文字以上               → 主表示 = 姓頭2 + 名末尾1
          * それ以外は 主表示 = 本質
    返却: (side_face, face_expr, side_core, core_expr, side_main, main_expr)
    """
    fN, gN = len(fchars), len(gchars)

    def lab(ch):  # f"{ch}({st})"
        return f"{ch}({tbl.stroke(ch)})"

    # 本質
    head_core_st = 1 if fN == 1 else (tbl.stroke(fchars[0]) if fN >= 1 else 0)
    head_core_lb = "霊(1)" if fN == 1 else (lab(fchars[0]) if fN >= 1 else "0")
    tail_core_st = 1 if gN == 1 else (tbl.stroke(gchars[-1]) if gN >= 1 else 0)
    tail_core_lb = "霊(1)" if gN == 1 else (lab(gchars[-1]) if gN >= 1 else "0")
    side_core = head_core_st + tail_core_st
    core_expr = f"{head_core_lb}+{tail_core_lb}={side_core}"

    # 表面
    head_face_st = 1 if fN == 1 else (tbl.stroke(fchars[0]) if fN >= 1 else 0)
    head_face_lb = "霊(1)" if fN == 1 else (lab(fchars[0]) if fN >= 1 else "0")
    if gN >= 2:
        last2 = gchars[-2:]
        face_list_lb = [lab(ch) for ch in last2]
        face_sum = sum(tbl.stroke(ch) for ch in last2)
    elif gN == 1:
        face_list_lb = [lab(gchars[-1]), "霊(1)"]  # 名1 → 末尾 + 霊
        face_sum = tbl.stroke(gchars[-1]) + 1
    else:
        face_list_lb = []
        face_sum = 0
    side_face = head_face_st + face_sum
    face_expr = f"{head_face_lb}+{'+'.join(face_list_lb) if face_list_lb else '0'}={side_face}"

    # 例外の主表示
    if fN >= 3 and gN >= 3:
        # 姓頭2 + 名末尾2
        ff = fchars[:2]
        gg = gchars[-2:]
        side_main = sum(tbl.stroke(ch) for ch in ff) + sum(tbl.stroke(ch) for ch in gg)
        main_expr = f"{'+'.join(lab(ch) for ch in ff)}+{'+'.join(lab(ch) for ch in gg)}={side_main}"
    elif fN >= 3:
        # 姓頭2 + 名末尾1
        ff = fchars[:2]
        gg = [gchars[-1]] if gN >= 1 else []
        side_main = sum(tbl.stroke(ch) for ch in ff) + sum(tbl.stroke(ch) for ch in gg)
        main_expr = f"{'+'.join(lab(ch) for ch in ff)}+{'+'.join(lab(ch) for ch in gg) if gg else '0'}={side_main}"
    else:
        side_main = side_core
        main_expr = core_expr

    return side_face, face_expr, side_core, core_expr, side_main, main_expr


def calc_full(family: str, given: str) -> dict:
    """
    すべての値と数式文字列、ブラケット表示用のラベル、内訳表情報を返す
    戻り値の主なキー:
      - top, heart, foot, side, side_face, side_core, allv
      - top_expr, heart_expr, foot_expr, side_main_expr, side_face_expr, side_core_expr, all_expr
      - family_labels, given_labels（各 '字(画)' のリスト）
      - table_rows: [(区分, 文字, 画数)] 霊数行も含む（総格には含めない）
    """
    tbl = StrokeTable()

    f = normalize_name(family)
    g = normalize_name(given)
    fchars = list(f)
    gchars = list(g)

    # 画数リスト・ラベル
    f_labels = _labels(fchars, tbl)
    g_labels = _labels(gchars, tbl)
    f_sum = _sum_strokes(fchars, tbl)
    g_sum = _sum_strokes(gchars, tbl)

    # 霊数
    reisu_head = 1 if len(fchars) == 1 else 0
    reisu_tail = 1 if len(gchars) == 1 else 0

    # トップ（天格）・・・姓合計 + 霊(姓1)
    top = f_sum + (1 if len(fchars) == 1 else 0)
    top_expr = f"{'霊(1)+' if reisu_head else ''}{'+'.join(f_labels) if f_labels else '0'}={top}"

    # ハート（人格）・・・姓末 + 名頭
    h_left = tbl.stroke(fchars[-1]) if fchars else 0
    h_right = tbl.stroke(gchars[0]) if gchars else 0
    heart = h_left + h_right
    heart_expr = f"{(f_labels[-1] if f_labels else '0')}+{(g_labels[0] if g_labels else '0')}={heart}"

    # フット（地格）・・・名合計 + 霊(名1)
    foot = g_sum + (1 if len(gchars) == 1 else 0)
    foot_expr = f"{'+'.join(g_labels) if g_labels else '0'}{'+霊(1)' if reisu_tail else ''}={foot}"

    # サイド（表面/本質/主表示）
    side_face, face_expr, side_core, core_expr, side, side_main_expr = _side_values(fchars, gchars, tbl)

    # オール（総格）・・・姓＋名（霊は含めない）→ 60超え折り返し
    all_raw = f_sum + g_sum
    allv = _wrap60(all_raw)
    all_expr = f"{'+'.join(f_labels + g_labels) if (f_labels or g_labels) else '0'}={all_raw}{('→' + str(allv)) if allv != all_raw else ''}"

    # 文字ごとの内訳表（霊数も表示）
    rows = []
    for ch in fchars:
        rows.append(("姓", ch, tbl.stroke(ch)))
    for ch in gchars:
        rows.append(("名", ch, tbl.stroke(ch)))
    if reisu_head:
        rows.append(("霊", "霊", 1))
    if reisu_tail:
        rows.append(("霊", "霊", 1))

    return {
        # 値
        "top": top,
        "heart": heart,
        "foot": foot,
        "side": side,  # 主表示
        "side_face": side_face,
        "side_core": side_core,
        "allv": allv,
        # 式文字列
        "top_expr": top_expr,
        "heart_expr": heart_expr,
        "foot_expr": foot_expr,
        "side_main_expr": side_main_expr,
        "side_face_expr": face_expr,
        "side_core_expr": core_expr,
        "all_expr": all_expr,
        # ブラケット図で使うラベル（'字(画)'）
        "family_labels": f_labels,
        "given_labels": g_labels,
        # テーブル
        "table_rows": rows,
    }
