# -*- coding: utf-8 -*-
import os
import io
import pandas as pd
import streamlit as st
from seimei_calc import load_dict, calc  # ← _load_dict は使わない

st.set_page_config(page_title="姓名判断（5格）", layout="wide")
st.title("姓名判断（5格）")

# 固定辞書: リポジトリ直下の kanji_master_joyo.csv を使う
DICT_PATH = os.path.join(os.path.dirname(__file__), "kanji_master_joyo.csv")

# 入力UI
with st.form("main_form"):
    col1, col2 = st.columns(2)
    with col1:
        family = st.text_input("姓", value="")
    with col2:
        given = st.text_input("名", value="")
    submitted = st.form_submit_button("計算する")

# 送信前は何も計算しない（NameError 回避）
if not submitted:
    st.info("姓名を入力して「計算する」を押してください。")
    st.stop()

# ここから安全に計算
try:
    table = load_dict(DICT_PATH)
except Exception as e:
    st.error(f"辞書の読み込みに失敗しました: {e}")
    st.stop()

res = calc(family, given, table)

# ---- 数値エリア（サマリー） -------------------------------------------------
st.header("結果")

cols = st.columns(5)
cols[0].metric("トップ（天格）", res["トップ（天格）"])
cols[1].metric("ハート（人格）", res["ハート（人格）"])
cols[2].metric("フット（地格）", res["フット（地格）"])

# サイドは「表面/本質」を可読表示
side_surface = res.get("サイド（表面）")
side_essence = res.get("サイド（本質）")
side_main = res.get("サイド（外格）", side_essence if side_essence is not None else side_surface)
side_label = f"{side_main}（表面={side_surface}, 本質={side_essence}）"
cols[3].metric("サイド（外格）", side_label)

cols[4].metric("オール（総格）", res["オール（総格）"])

# ---- 内訳テーブル -----------------------------------------------------------
st.subheader("文字ごとの内訳（霊数も表示）")
# res["breakdown"] は [(区分, 文字, 画数)] の想定
bd = res.get("breakdown", [])
if bd:
    df = pd.DataFrame(bd, columns=["区分", "文字", "画数"])
    st.dataframe(df, use_container_width=True)

# ---- 文字列展開の「実際の計算式」表示 ---------------------------------------
def fmt_term(ch, strokes):
    return f"{ch}（{strokes}）"

def join_terms(terms):
    return " + ".join(terms)

eq_top = join_terms([fmt_term(*t) for t in res["_式"]["トップ"]]) + f" ＝ {res['トップ（天格）']}"
eq_heart = join_terms([fmt_term(*t) for t in res["_式"]["ハート"]]) + f" ＝ {res['ハート（人格）']}"
eq_foot = join_terms([fmt_term(*t) for t in res["_式"]["フット"]]) + f" ＝ {res['フット（地格）']}"

# サイド（表面／本質）
eq_side_surface = join_terms([fmt_term(*t) for t in res["_式"]["サイド表面"]]) + f" ＝ {side_surface}"
eq_side_essence = join_terms([fmt_term(*t) for t in res["_式"]["サイド本質"]]) + f" ＝ {side_essence}"

eq_all = join_terms([fmt_term(*t) for t in res["_式"]["オール"]]) + f" ＝ {res['オール（総格）']}"

st.subheader("実際の計算式（テキスト）")
st.write(f"トップ＝{eq_top}")
st.write(f"ハート＝{eq_heart}")
st.write(f"フット＝{eq_foot}")
st.write(f"サイド（表面）＝{eq_side_surface}")
st.write(f"サイド（本質）＝{eq_side_essence}")
st.write(f"オール＝{eq_all}")

# ---- ブラケット図（簡易） ---------------------------------------------------
import matplotlib
matplotlib.use("Agg")  # サーバーでの描画安定化
import matplotlib.pyplot as plt

def draw_bracket_figure(res_dict):
    fig, ax = plt.subplots(figsize=(8, 3), dpi=150)
    ax.axis("off")

    family_terms = [fmt_term(ch, s) for ch, s in res_dict["_式"]["姓"]]
    given_terms  = [fmt_term(ch, s) for ch, s in res_dict["_式"]["名"]]

    top_v   = res_dict["トップ（天格）"]
    heart_v = res_dict["ハート（人格）"]
    foot_v  = res_dict["フット（地格）"]
    side_v  = res_dict["サイド（外格）"]
    all_v   = res_dict["オール（総格）"]

    y0 = 0.8
    x0 = 0.05
    dy = 0.18

    ax.text(x0, y0, "姓：" + "・".join(family_terms), fontsize=11, transform=ax.transAxes)
    ax.text(x0, y0 - dy, "名：" + "・".join(given_terms), fontsize=11, transform=ax.transAxes)

    ax.text(0.55, y0,     f"トップ → {top_v}", fontsize=11, transform=ax.transAxes)
    ax.text(0.55, y0-dy,  f"ハート → {heart_v}", fontsize=11, transform=ax.transAxes)
    ax.text(0.55, y0-2*dy,f"フット → {foot_v}", fontsize=11, transform=ax.transAxes)
    ax.text(0.55, y0-3*dy,f"サイド → {side_v}", fontsize=11, transform=ax.transAxes)

    ax.hlines(0.1, 0.05, 0.95, transform=ax.transAxes, color="black", linewidth=1.0)
    ax.text(0.5, 0.04, f"オール → {all_v}", fontsize=11, ha="center", transform=ax.transAxes)

    return fig

st.subheader("図解（ブラケット図）")
fig = draw_bracket_figure(res)
st.pyplot(fig)
plt.close(fig)
