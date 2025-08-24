# -*- coding: utf-8 -*-
"""
姓名判断（5格）コアロジック
- 固定辞書: kanji_master_joyo.csv（同リポジトリ直下に置く）
- 文字単位の画数オーバーライド: kanji_overrides.csv（任意・同ディレクトリ）
- 霊数・サイドのルールはユーザー指定の完全版に準拠
"""

from __future__ import annotations
import csv
import unicodedata
from pathlib import Path
from typing import Dict, List, Tuple, Optional

#========================
# 正規化・異体字・繰り返し
#========================
VARIANT_MAP = {
    "禎": "祓",
    "琢": "琢",
    "穀": "穀",
    "祝": "祝",
}
REPEAT_MARK = "々"

#========================
# オーバーライド読み込み
#========================
def _load_overrides() -> Dict[str, int]:
    """
    同ディレクトリの kanji_overrides.csv（char,strokes）を読み取る。
    例：
      char,strokes
      海,11
    """
    here = Path(__file__).resolve().parent
    path = here / "kanji_overrides.csv"
    data: Dict[str, int] = {}
    if not path.exists():
        return data
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ch = (row.get("char") or "").strip()
            st = (row.get("strokes") or "").strip()
            if not ch or not st:
                continue
            try:
                data[ch] = int(st)
            except ValueError:
                pass
    return data

_KANJI_OVERRIDES = _load_overrides()

#========================
# 辞書（常用）読み込み
#========================
def load_dict_fixed() -> Dict[str, int]:
    """
    リポジトリ直下の kanji_master_joyo.csv を読み込む。
    想定ヘッダー: kanji,strokes_old
    """
    repo_root = Path(__file__).resolve().parent
    # アプリは同じディレクトリに置く想定
    csv_path = (repo_root / "kanji_master_joyo.csv").resolve()
    d: Dict[str, int] = {}
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
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

#========================
# ユーティリティ
#========================
def normalize_name(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    chars: List[str] = []
    for ch in s:
        ch = VARIANT_MAP.get(ch, ch)
        if ch == REPEAT_MARK and chars:
            ch = chars[-1]
        chars.append(ch)
    return "".join(chars)

def stroke_for_char(ch: str, table: Dict[str, int]) -> int:
    """最優先: overrides → 辞書"""
    if ch in _KANJI_OVERRIDES:
        return _KANJI_OVERRIDES[ch]
    return table.get(ch, 0)

def strokes_of_str(s: str, table: Dict[str, int]) -> Tuple[int, List[Tuple[str,int]]]:
    total = 0
    lst: List[Tuple[str,int]] = []
    for ch in s:
        st = stroke_for_char(ch, table)
        lst.append((ch, st))
        total += st
    return total, lst

def wrap_60(n: int) -> int:
    """60超えは 1..60 で循環（例: 63 → 3）"""
    if n <= 0:
        return 0
    return ((n - 1) % 60) + 1

#========================
# サイド計算（ルール準拠）
#========================
def _head_parts_for_side(fchars: List[str], table: Dict[str,int]) -> List[Tuple[str,int]]:
    """
    サイドの「頭」側の構成要素（文字と画数の並び）を返す。
    - 姓が1文字 … [("霊",1), (姓1)]
    - 姓が3文字以上 … [(姓1),(姓2)]
    - それ以外 … [(姓1)]
    """
    parts: List[Tuple[str,int]] = []
    if not fchars:
        return parts
    if len(fchars) == 1:
        parts.append(("霊数", 1))
        parts.append((fchars[0], stroke_for_char(fchars[0], table)))
    elif len(fchars) >= 3:
        parts.append((fchars[0], stroke_for_char(fchars[0], table)))
        parts.append((fchars[1], stroke_for_char(fchars[1], table)))
    else:
        parts.append((fchars[0], stroke_for_char(fchars[0], table)))
    return parts

def _tail_ess_for_side(gchars: List[str], table: Dict[str,int]) -> List[Tuple[str,int]]:
    """
    サイド「本質」の末尾側
    - 名前1文字 … [("霊",1)]  ← 例: 原野 武 → 頭 + 霊数
    - 名前2文字 … [(末尾1)]
    - 名前3文字以上 … [(末尾1)]
    """
    parts: List[Tuple[str,int]] = []
    if not gchars:
        return parts
    if len(gchars) == 1:
        parts.append(("霊数", 1))
    else:
        last = gchars[-1]
        parts.append((last, stroke_for_char(last, table)))
    return parts

def _tail_surf_for_side(gchars: List[str], table: Dict[str,int]) -> Optional[List[Tuple[str,int]]]:
    """
    サイド「表面」の末尾側
    - 名前3文字以上 … [(末尾2),(末尾1)]
    - それ以外 … None（表面は定義しない）
    """
    if not gchars or len(gchars) < 3:
        return None
    last2 = gchars[-2]
    last1 = gchars[-1]
    return [
        (last2, stroke_for_char(last2, table)),
        (last1, stroke_for_char(last1, table)),
    ]

def _join_sum(parts: List[Tuple[str,int]]) -> Tuple[int, str]:
    """
    [("原",10),("野",11)] → (21, "原(10)+野(11)=21")
    """
    total = sum(st for _, st in parts)
    formula = " + ".join(f"{ch}({st})" for ch, st in parts) + f" = {total}"
    return total, formula

#========================
# メイン計算
#========================
def calc(family: str, given: str, table: Dict[str,int]) -> Dict:
    f = normalize_name(family or "")
    g = normalize_name(given or "")
    fchars = list(f)
    gchars = list(g)

    # トップ（天格）
    f_sum, f_list = strokes_of_str(f, table)
    if len(fchars) == 1:
        top_val = f_sum + 1
        top_formula = f"霊数(1) + " + " + ".join([f"{ch}({st})" for ch,st in f_list]) + f" = {top_val}"
    else:
        top_val = f_sum
        top_formula = " + ".join([f"{ch}({st})" for ch,st in f_list]) + f" = {top_val}"

    # フット（地格）
    g_sum, g_list = strokes_of_str(g, table)
    if len(gchars) == 1 and gchars:
        foot_val = g_sum + 1
        foot_formula = " + ".join([f"{ch}({st})" for ch,st in g_list]) + " + 霊数(1)" + f" = {foot_val}"
    else:
        foot_val = g_sum
        if g_list:
            foot_formula = " + ".join([f"{ch}({st})" for ch,st in g_list]) + f" = {foot_val}"
        else:
            foot_formula = "0 = 0"

    # ハート（人格）＝ 姓末字 + 名先頭字（片方無ければ0）
    if fchars and gchars:
        heart_left = (fchars[-1], stroke_for_char(fchars[-1], table))
        heart_right = (gchars[0], stroke_for_char(gchars[0], table))
        heart_val = heart_left[1] + heart_right[1]
        heart_formula = f"{heart_left[0]}({heart_left[1]}) + {heart_right[0]}({heart_right[1]}) = {heart_val}"
    else:
        heart_val = 0
        heart_formula = "0 = 0"

    # サイド（外格）
    head_parts = _head_parts_for_side(fchars, table)
    tail_ess = _tail_ess_for_side(gchars, table)
    tail_surf = _tail_surf_for_side(gchars, table)

    ess_total, ess_formula_inner = _join_sum(head_parts + tail_ess)
    side_ess_val = ess_total
    side_ess_formula = ess_formula_inner

    side_surf_val: Optional[int] = None
    side_surf_formula: Optional[str] = None

    # 例外：姓・名ともに3文字以上 → サイドは頭2 + 末尾2（表面/本質の区別は設けず単一値）
    if len(fchars) >= 3 and len(gchars) >= 3:
        # 頭2は head_parts がすでに [(姓1),(姓2)]
        tail2 = tail_surf or []
        val, formula = _join_sum(head_parts + tail2)
        side_val = val
        side_formula_show = formula
        side_note = None
    else:
        # 家族が3文字以上（名が2以下） → 頭2 + 末尾1（本質のみ）
        if len(fchars) >= 3 and len(gchars) <= 2:
            side_val = side_ess_val
            side_formula_show = side_ess_formula
            side_note = "（本質）"
        # 名前が3文字以上（姓は1〜2） → 本質（頭 + 末尾1）/ 表面（頭 + 末尾2）の2本
        elif len(gchars) >= 3:
            side_val = side_ess_val
            side_formula_show = side_ess_formula
            side_note = "（本質）"
            if tail_surf:
                surf_total, surf_formula_inner = _join_sum(head_parts + tail_surf)
                side_surf_val = surf_total
                side_surf_formula = surf_formula_inner  # 表示用
        # 名前1文字 → 本質（頭 + 霊数）だけ
        elif len(gchars) == 1:
            side_val = side_ess_val
            side_formula_show = side_ess_formula
            side_note = "（本質）"
        else:
            side_val = side_ess_val
            side_formula_show = side_ess_formula
            side_note = None

    # オール（総格）＝ 姓＋名の合計（霊数除外）
    all_val_raw = f_sum + g_sum
    all_val = wrap_60(all_val_raw)
    all_formula = f"{f}({f_sum}) + {g}({g_sum}) = {all_val_raw} → {all_val}"

    # 文字ごとの表（霊数も表示）
    per_chars: List[Tuple[str,str,int]] = []
    for ch, st in f_list:
        per_chars.append(("姓", ch, st))
    for ch, st in g_list:
        per_chars.append(("名", ch, st))
    # 霊数の見える化（姓1文字先頭／名1文字末尾）
    if len(fchars) == 1 and fchars:
        per_chars.insert(0, ("姓", "霊", 1))
    if len(gchars) == 1 and gchars:
        per_chars.append(("名", "霊", 1))

    return {
        "numbers": {
            "top": top_val,
            "heart": heart_val,
            "foot": foot_val,
            "side": side_val,
            "side_surf": side_surf_val,
            "all": all_val,
            "all_raw": all_val_raw,
        },
        "formulas": {
            "top": top_formula,
            "heart": heart_formula,
            "foot": foot_formula,
            "side": side_formula_show + (side_note or ""),
            "side_surf": side_surf_formula,  # ないときは None
            "all": all_formula,
        },
        "chars": per_chars,
        "meta": {
            "family": f,
            "given": g,
        },
    }
