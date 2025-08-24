# -*- coding: utf-8 -*-
import os
import csv
import sys
import unicodedata
import streamlit as st

# --- matplotlib は任意。無ければ図解表示をスキップ ---
try:
    import matplotlib.pyplot as plt
    HAS_MPL = True
except Exception:
    plt = None
    HAS_MPL = False

# ======================================
# 基本設定
# ======================================
DICT_FILE = "kanji_master_joyo.csv"      # 固定の辞書
OVERRIDES_FILE = "kanji_overrides.csv"   # 任意。なければ無視

REPEAT_MARK = "々"  # くり返し
REI = 1            # 霊数は「1」

# 一部の互換漢字の統一（必要に応じて追加）
VARIANT_MAP = {
    "禎": "祓",
    "琢": "琢",
    "穀": "穀",
    "祝": "祝",
}

# ======================================
# 読み込み系
# ======================================
def _safe_path(name: str) -> str:
    return os.path.join(os.path.dirname(__file__), name)

def load_dict(csv_path: str) -> dict:
    """kanji_master_joyo.csv を読み込む（key=kanji, value=strokes_old）"""
    d = {}
    with open(_safe_path(csv_path), "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            k = (r.get("kanji") or "").strip()
            v = (r.get("strokes_old") or "").strip()
            if not k:
                continue
            try:
                d[k] = int(v)
            except:
                d[k] = 0
    return d

def load_overrides() -> dict:
    """kanji_overrides.csv を読み込む（任意）"""
    path = _safe_path(OVERRIDES_FILE)
    data = {}
    if not os.path.exists(path):
        return data
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ch = (row.get("char") or "").strip()
            stv = (row.get("strokes") or "").strip()
            if not ch or not stv:
                continue
            try:
                data[ch] = int(stv)
            except:
                pass
    return data

_KANJI = load_dict(DICT_FILE)
_KANJI_OVERRIDES = load_overrides()

# ======================================
# ユーティリティ
# ======================================
def normalize_name(s: str) -> str:
    """NFKC 正規化＋互換漢字統一＋々対応"""
    s = unicodedata.normalize("NFKC", s)
    chars = []
    for ch in s:
        ch = VARIANT_MAP.get(ch, ch)
        if ch == REPEAT_MARK and chars:
            ch = chars[-1]
        chars.append(ch)
    return "".join(chars)

def stroke_for_char(ch: str, table: dict) -> int:
    """個別オーバーライドが最優先、なければ辞書"""
    if ch in _KANJI_OVERRIDES:
        return _KANJI_OVERRIDES[ch]
    return table.get(ch, 0)

def strokes_of(name: str, table: dict) -> int:
    """純粋な合計（霊数は含めない）"""
    total = 0
    for ch in name:
        total += stroke_for_char(ch, table)
    return total

def wrap_to_60(n: int) -> int:
    """60 を超えたら 1 から数え直す"""
    if n <= 60:
        return n
    return ((n - 1) % 60) + 1

# サイド用ヘッド（姓）
def head_value_for_side(fchars, table) -> int:
    if not fchars:
        return 0
    if len(fchars) >= 3:
        return stroke_for_char(fchars[0], table) + stroke_for_char(fchars[1], table)
    if len(fchars) == 1:
        return REI  # 姓が1文字 → ヘッドは霊
    # 2文字
    return stroke_for_char(fchars[0], table)

# サイド用テイル（名・本質＝末尾1 / 表面＝末尾2）
def tail1_for_side(gchars, table) -> int:
    if not gchars:
        return 0
    if len(gchars) == 1:
        return REI  # 名が1文字 → 末尾は霊
    return stroke_for_char(gchars[-1], table)

def tail2_for_side(gchars, table) -> int:
    if not gchars:
        return 0
    if len(gchars) >= 2:
        return stroke_for_char(gchars[-2], table) + stroke_for_char(gchars[-1], table)
    # 1文字 → 末尾2 の代わりに (末尾1 + 霊)
    return stroke_for_char(gchars[-1], table) + REI

# ======================================
# メイン計算
# ======================================
def calc(family: str, given: str, table: dict) -> dict:
    f = normalize_name(family)
    g = normalize_name(given)
    fchars = list(f)
    gchars = list(g)

    # トップ（姓合計 + 頭霊数）
    top = strokes_of(f, table) + (REI if len(fchars) == 1 else 0)

    # フット（名合計 + 末尾霊数）
    foot = strokes_of(g, table) + (REI if len(gchars) == 1 else 0)

    # ハート（姓末 + 名頭）
    if fchars and gchars:
        heart = stroke_for_char(fchars[-1], table) + stroke_for_char(gchars[0], table)
    else:
        heart = 0

    # サイド（本質／表面）
    head = head_value_for_side(fchars, table)
    ess_tail = tail1_for_side(gchars, table)

    if len(fchars) >= 3 and len(gchars) >= 3:
        # 例外：姓・名とも3文字以上 → 頭2 + 末尾2 が表面
        surf_tail_val = stroke_for_char(gchars[-2], table) + stroke_for_char(gchars[-1], table)
    else:
        surf_tail_val = tail2_for_side(gchars, table)

    side_ess = head + ess_tail
    side_surface = head + surf_tail_val
    side = max(side_ess, side_surface)

    # オール（姓＋名合計。霊は含めない）
    allv = wrap_to_60(strokes_of(f, table) + strokes_of(g, table))

    return {
        "トップ（天格）": top,
        "ハート（人格）": heart,
        "フット（地格）": foot,
        "サイド": side,
        "サイド（本質）": side_ess,
        "サイド（表面）": side_surface,
        "オール（総格）": allv,
        "family_norm": f,
        "given_norm": g,
    }

# ======================================
# 文字→式の表示支援
# ======================================
def fmt_terms(chars, table):
    return [(ch, stroke_for_char(ch, table)) for ch in chars]

def fmt_sum(terms, extra=None):
    parts = [f"{ch}({st})" for ch, st in terms]
    if extra is not None:
        parts.append(f"{extra[0]}({extra[1]})")
    total = sum(st for _, st in terms) + (extra[1] if extra else 0)
    return " + ".join(parts) + f" = {total}"

def make_breakdown_text(f, g, table, res):
    fchars = list(f)
    gchars = list(g)

    # トップ
    top_terms = fmt_terms(fchars, table)
    top_extra = ("霊", REI) if len(fchars) == 1 else None
    top_line = f"トップ ＝ {fmt_sum(top_terms, top_extra)}"

    # ハート
    if fchars and gchars:
        heart_terms = [(fchars[-1], stroke_for_char(fchars[-1], table)),
                       (gchars[0], stroke_for_char(gchars[0], table))]
        heart_line = f"ハート ＝ {fmt_sum(heart_terms)}"
    else:
        heart_line = "ハート ＝ 0"

    # フット
    foot_terms = fmt_terms(gchars, table)
    foot_extra = ("霊", REI) if len(gchars) == 1 else None
    foot_line = f"フット ＝ {fmt_sum(foot_terms, foot_extra)}"

    # サイド（本質/表面）表示
    if len(fchars) >= 3:
        f_head_terms = [(fchars[0], stroke_for_char(fchars[0], table)),
                        (fchars[1], stroke_for_char(fchars[1], table))]
    elif len(fchars) == 1:
        f_head_terms = [("霊", REI)]
    else:
        f_head_terms = [(fchars[0], stroke_for_char(fchars[0], table))]

    if len(gchars) == 1:
        ess_tail = [("霊", REI)]
    else:
        ess_tail = [(gchars[-1], stroke_for_char(gchars[-1], table))]

    if len(fchars) >= 3 and len(gchars) >= 3:
        surf_tail = [
            (gchars[-2], stroke_for_char(gchars[-2], table)),
            (gchars[-1], stroke_for_char(gchars[-1], table)),
        ]
    else:
        if len(gchars) >= 2:
            surf_tail = [
                (gchars[-2], stroke_for_char(gchars[-2], table)),
                (gchars[-1], stroke_for_char(gchars[-1], table)),
            ]
        else:
            surf_tail = [
                (gchars[-1], stroke_for_char(gchars[-1], table)),
                ("霊", REI),
            ]

    side_ess_line = (
        "サイド（本質） ＝ "
        + fmt_sum(f_head_terms + ess_tail)
        + f"（＝ {res['サイド（本質）']}）"
    )
    side_surf_line = (
        "サイド（表面） ＝ "
        + fmt_sum(f_head_terms + surf_tail)
        + f"（＝ {res['サイド（表面）']}）"
    )
    side_line = f"サイド ＝ {res['サイド']}（表面と本質の大きい方）"

    # オール（霊は含めない）
    all_terms = fmt_terms(fchars + gchars, table)
    all_total = sum(st for _, st in all_terms)
    all_line = "オール ＝ " + " + ".join([f"{ch}({st})" for ch, st in all_terms]) + f" = {all_total}"
    if all_total > 60:
        all_line += f" → 60超えのため 1 から数え直し ＝ {res['オール（総格）']}"

    return [top_line, heart_line, foot_line, side_ess_line, side_surf_line, side_line, all_line]

# ======================================
# 図解（matplotlib がある場合のみ）
# ======================================
def draw_layout_figure(family: str, given: str, table: dict, res: dict):
    fchars = list(family)
    gchars = list(given)

    rei_head = (len(fchars) == 1)
    rei_tail = (len(gchars) == 1)

    def terms(chars):
        return [(ch, stroke_for_char(ch, table)) for ch in chars]

    f_terms = terms(fchars)
    g_terms = terms(gchars)

    fig_w, fig_h = 8.5, 6.0
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=160)
    ax.set_axis_off()
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)

    title = f"{family} {given}　さんの姓名判断結果"
    ax.text(50, 94, title, ha="center", va="center", fontsize=13, fontweight="bold")
    ax.text(50, 88, f"オール {res['オール（総格）']}", ha="center", va="center", fontsize=12)

    X_NAME = 36
    X_STROKE = 44
    X_ARROW = 68
    LINE_H = 8
    START_Y = 78

    def draw_column(x_char, x_stroke, start_y, items, label_top=None, label_bottom=None):
        y = start_y
        y_top = y
        for ch, s in items:
            ax.text(x_char, y, f"{ch}", ha="center", va="center", fontsize=13)
            ax.text(x_stroke, y, f"{s}", ha="center", va="center", fontsize=11)
            y -= LINE_H
        y_bottom = y + LINE_H
        if label_top:
            ax.text(x_char - 5, y_top + 3, label_top, ha="right", va="center", fontsize=11)
        if label_bottom:
            ax.text(x_char - 5, y_bottom - 3, label_bottom, ha="right", va="center", fontsize=11)
        return y_top, y_bottom

    f_top, f_bottom = draw_column(
        X_NAME, X_STROKE, START_Y, f_terms, label_top=("霊" if rei_head else None)
    )
    g_top, g_bottom = draw_column(
        X_NAME, X_STROKE, START_Y, g_terms, label_bottom=("霊" if rei_tail else None)
    )

    def bracket(x, y_top, y_bottom, width=6):
        ax.plot([x, x + width], [y_top, y_top], color="black", lw=1.5)
        ax.plot([x, x], [y_top, y_bottom], color="black", lw=1.5)
        ax.plot([x, x + width], [y_bottom, y_bottom], color="black", lw=1.5)

    bracket(X_NAME - 6, f_top + 3, f_bottom - 3)
    bracket(X_NAME - 6, g_top + 3, g_bottom - 3)

    ax.annotate(f"{res['トップ（天格）']} → トップ・・・血統",
                xy=(X_STROKE + 3, (f_top + f_bottom) / 2),
                xytext=(X_ARROW, (f_top + f_bottom) / 2),
                fontsize=11, ha="left", va="center",
                arrowprops=dict(arrowstyle="->", lw=1.2))

    ax.annotate(f"{res['ハート（人格）']} → ハート・・・性格・愛情",
                xy=(X_STROKE + 3, (f_bottom + g_top) / 2),
                xytext=(X_ARROW, (f_bottom + g_top) / 2),
                fontsize=11, ha="left", va="center",
                arrowprops=dict(arrowstyle="->", lw=1.2))

    ax.annotate(f"{res['フット（地格）']} → フット・・・恋愛",
                xy=(X_STROKE + 3, (g_top + g_bottom) / 2),
                xytext=(X_ARROW, (g_top + g_bottom) / 2),
                fontsize=11, ha="left", va="center",
                arrowprops=dict(arrowstyle="->", lw=1.2))

    side_val = res.get("サイド", 0)
    side_surf = res.get("サイド（表面）", None)
    side_ess = res.get("サイド（本質）", None)
    if side_surf is not None and side_ess is not None and side_surf != side_ess:
        side_text = f"職業・・・サイド ← {side_val}（表面={side_surf}, 本質={side_ess}）"
    else:
        side_text = f"職業・・・サイド ← {side_val}"
    ax.text(22, (f_bottom + g_top) / 2, side_text, ha="left", va="center", fontsize=11)

    ax.plot([20, 80], [18, 18], color="black", lw=1)
    ax.text(50, 12, f"{res['オール（総格）']}  → オール・・・全体", ha="center", va="center", fontsize=12)
    ax.text(50, 5.5, "※霊は “1” の意。総格（オール）には含めません。", ha="center", va="center", fontsize=9, color="#444")

    fig.tight_layout()
    return fig

# ======================================
# Streamlit UI
# ======================================
st.set_page_config(page_title="姓名判断（5格）", layout="centered")
st.title("姓名判断（5格）")

with st.form("main_form"):
    col1, col2 = st.columns(2)
    with col1:
        family = st.text_input("姓", value="")
    with col2:
        given = st.text_input("名", value="")
    submitted = st.form_submit_button("計算する")

if submitted:
    try:
        f = normalize_name(family)
        g = normalize_name(given)
        res = calc(family, given, _KANJI)

        # --- 数値の表示 ---
        st.subheader("結果")
        colA, colB, colC, colD, colE = st.columns(5)
        with colA:
            st.metric("トップ（天格）", res["トップ（天格）"])
        with colB:
            st.metric("ハート（人格）", res["ハート（人格）"])
        with colC:
            st.metric("フット（地格）", res["フット（地格）"])
        with colD:
            st.metric("サイド（外格）", f"{res['サイド']}（表面={res['サイド（表面）']}, 本質={res['サイド（本質）']}）")
        with colE:
            st.metric("オール（総格）", res["オール（総格）"])

        # --- 式の表示 ---
        st.write("---")
        st.subheader("計算式（式をそのまま表示）")
        for line in make_breakdown_text(f, g, _KANJI, res):
            st.markdown(line)

        # --- 文字ごとの内訳（霊も表示） ---
        st.write("---")
        st.subheader("文字ごとの内訳（霊数も表示）")
        table_rows = []
        for ch in list(f):
            table_rows.append(("姓", ch, stroke_for_char(ch, _KANJI)))
        for ch in list(g):
            table_rows.append(("名", ch, stroke_for_char(ch, _KANJI)))
        if len(list(f)) == 1:
            table_rows.append(("霊（頭）", "霊", REI))
        if len(list(g)) == 1:
            table_rows.append(("霊（末）", "霊", REI))

        import pandas as pd
        df = pd.DataFrame(table_rows, columns=["区分", "文字", "画数"])
        st.dataframe(df, use_container_width=True, hide_index=True)

        # --- 図解（ブラケット図） ---
        st.write("---")
        st.subheader("図解（ブラケット図）")
        if HAS_MPL:
            fig = draw_layout_figure(f, g, _KANJI, res)
            st.pyplot(fig, use_container_width=True)
        else:
            st.info(
                "図解の表示には matplotlib が必要です。"
                "リポジトリの requirements.txt に `matplotlib` を追加して再デプロイしてください。"
            )

    except Exception as e:
        st.error(f"計算時にエラーが発生しました: {e}")

else:
    st.info("姓と名を入力して「計算する」を押してください。")
