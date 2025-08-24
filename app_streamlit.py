# -*- coding: utf-8 -*-
"""
Streamlit アプリ
- 固定辞書: kanji_master_joyo.csv を常用
- 画数の例外は kanji_overrides.csv に追加して運用
- 図解は Matplotlib を "Agg" バックエンドで描画し、確実に close する
"""

import os
# === ここが安定化ポイント ===
os.environ["MPLCONFIGDIR"] = "/tmp/mpl"
import matplotlib
matplotlib.use("Agg")  # GUI不要のバックエンド
import matplotlib.pyplot as plt

import pandas as pd
import streamlit as st
from pathlib import Path

from seimei_calc import calc, load_dict_fixed

# ----------------------------
# 初期ロード
# ----------------------------
@st.cache_resource
def _load_table():
    return load_dict_fixed()

TABLE = _load_table()

st.set_page_config(page_title="姓名判断（5格）", page_icon="🔢", layout="centered")

st.title("姓名判断（5格）")

# 入力欄（辞書選択は廃止・固定）
with st.form("main_form"):
    col1, col2 = st.columns(2)
    with col1:
        family = st.text_input("姓", value="", max_chars=10)
    with col2:
        given = st.text_input("名", value="", max_chars=10)
    submitted = st.form_submit_button("計算する")

def _draw_bracket_figure(res: dict):
    """
    シンプルなブラケット風の図解を描く。
    - テキスト中心（日本語フォント前提にしない）
    """
    fam = res["meta"]["family"]
    giv = res["meta"]["given"]
    nums = res["numbers"]
    fm = res["formulas"]

    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=160)
    ax.axis("off")

    # 中央タイトル
    title = f"{fam} {giv}　さんの姓名判断結果"
    ax.text(0.5, 0.94, title, ha="center", va="center", fontsize=13, fontweight="bold")

    # 上部：オール
    ax.text(0.5, 0.86, f"オール {nums['all']}  （{fm['all']}）", ha="center", va="center", fontsize=11)

    # 左カラム（姓と名のリストを段組で）
    y0 = 0.73
    ax.text(0.16, y0, "構成", ha="center", va="center", fontsize=11, fontweight="bold")
    # 文字列（姓＋名）
    fam_line = "　".join(list(fam)) if fam else "-"
    giv_line = "　".join(list(giv)) if giv else "-"
    ax.text(0.16, y0-0.06, f"姓：{fam_line}", ha="center", va="center", fontsize=10)
    ax.text(0.16, y0-0.12, f"名：{giv_line}",  ha="center", va="center", fontsize=10)

    # 右側：各格と式
    y = 0.73
    step = 0.11
    ax.text(0.48, y,     f"トップ（天格）  {nums['top']}  ←  {fm['top']}",   fontsize=10)
    ax.text(0.48, y-step, f"ハート（人格）  {nums['heart']}  ←  {fm['heart']}", fontsize=10)
    ax.text(0.48, y-2*step, f"フット（地格）  {nums['foot']}  ←  {fm['foot']}", fontsize=10)

    # サイド
    side_line = f"サイド（外格）  {nums['side']}  ←  {fm['side']}"
    ax.text(0.48, y-3*step, side_line, fontsize=10)
    if fm.get("side_surf"):
        ax.text(0.48, y-3*step-0.07, f"　　　　　　表面：{fm['side_surf']}", fontsize=10)

    # 下部注釈
    ax.text(0.5, 0.08, "※ 霊数は総格（オール）には含めません（各格には含めます）", ha="center", va="center", fontsize=9)

    fig.tight_layout()
    return fig

def _df_from_chars(res: dict) -> pd.DataFrame:
    rows = []
    for kind, ch, st in res["chars"]:
        rows.append({"区分": kind, "文字": ch, "画数": st})
    return pd.DataFrame(rows)

if submitted:
    res = calc(family, given, TABLE)

    st.header("結果")
    cols = st.columns(5)
    cols[0].metric("トップ（天格）", res["numbers"]["top"])
    cols[1].metric("ハート（人格）", res["numbers"]["heart"])
    cols[2].metric("フット（地格）", res["numbers"]["foot"])

    # サイド（表面があるときは括弧で併記）
    side_main = res["numbers"]["side"]
    side_surf = res["numbers"]["side_surf"]
    if side_surf is not None:
        side_label = f"{side_main}（表面={side_surf}）"
    else:
        side_label = str(side_main)
    cols[3].metric("サイド（外格）", side_label)
    cols[4].metric("オール（総格）", res["numbers"]["all"])

    # 計算式（テキスト）
    st.subheader("計算式（テキスト）")
    st.write(f"トップ＝{res['formulas']['top']}")
    st.write(f"ハート＝{res['formulas']['heart']}")
    st.write(f"フット＝{res['formulas']['foot']}")
    st.write(f"サイド＝{res['formulas']['side']}")
    if res["formulas"].get("side_surf"):
        st.write(f"　　　（表面）＝{res['formulas']['side_surf']}")
    st.write(f"オール＝{res['formulas']['all']}")

    # 文字ごとの内訳（霊数も見せる）
    st.subheader("文字ごとの内訳（霊数も表示）")
    st.dataframe(_df_from_chars(res), use_container_width=True)

    # 図解（ブラケット風）
    st.subheader("図解（ブラケット風）")
    fig = _draw_bracket_figure(res)
    st.pyplot(fig, clear_figure=True, use_container_width=True)
    plt.close(fig)  # 後始末（重要）
