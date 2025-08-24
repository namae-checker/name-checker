# -*- coding: utf-8 -*-
import os
import streamlit as st
import pandas as pd
from seimei_calc import load_dict, calc, stroke_for_char, normalize_name

st.set_page_config(page_title="姓名判断（5格・最終ルール対応）", layout="centered")
st.title("姓名判断（5格）")

@st.cache_data(show_spinner=False)
def list_dict_files() -> list:
    files = [f for f in os.listdir(".") if f.startswith("kanji_master_") and f.endswith(".csv")]
    files.sort()
    return files

def per_char_table(family: str, given: str, table: dict) -> pd.DataFrame:
    rows = []
    f = normalize_name(family)
    g = normalize_name(given)
    for ch in list(f):
        rows.append(("姓", ch, stroke_for_char(ch, table)))
    for ch in list(g):
        rows.append(("名", ch, stroke_for_char(ch, table)))
    return pd.DataFrame(rows, columns=["区分", "文字", "画数"])

dict_files = list_dict_files()
if not dict_files:
    st.error("kanji_master_*.csv が見つかりません。リポジトリ直下に配置してください。")
    st.stop()

with st.form("main_form", clear_on_submit=False):
    dict_name = st.selectbox("使用する辞書を選択", dict_files, index=0)
    c1, c2 = st.columns(2)
    with c1:
        family = st.text_input("姓", value="")
    with c2:
        given = st.text_input("名", value="")
    submitted = st.form_submit_button("計算する")

if not submitted:
    st.stop()

table = load_dict(dict_name)
res = calc(family, given, table)

st.subheader("結果")
st.metric("トップ（天格）",  res.get("トップ（天格）", 0))
st.metric("ハート（人格）",  res.get("ハート（人格）", 0))
st.metric("フット（地格）",  res.get("フット（地格）", 0))

# サイド表示：名が3文字以上なら（表面, 本質）併記。それ以外は本質のみ。
side_main = res.get("サイド（外格・本質）", 0)
side_surface = res.get("サイド（外格・表面）")
if side_surface is not None:
    st.metric("サイド（外格）", f"{side_main}（表面={side_surface}, 本質={side_main}）")
else:
    st.metric("サイド（外格）", side_main)

st.metric("オール（総格）", res.get("オール（総格）", 0))

# 文字ごとの内訳（参考）
df = per_char_table(family, given, table)
if not df.empty:
    st.subheader("文字ごとの内訳（霊数は表示に含めません）")
    st.dataframe(df, use_container_width=True)
