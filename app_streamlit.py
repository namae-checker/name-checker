# -*- coding: utf-8 -*-
import os
import streamlit as st

from seimei_calc import load_dict, calc

st.set_page_config(page_title="姓名判断（5格）", layout="centered")
st.title("姓名判断（5格）")

# 探索: 同ディレクトリにある kanji_master_*.csv から選択
dict_files = sorted(
    [f for f in os.listdir(".") if f.startswith("kanji_master_") and f.endswith(".csv")]
)

with st.form("main_form"):
    dict_name = st.selectbox("使用する辞書を選択", dict_files, index=0 if dict_files else 0)
    col1, col2 = st.columns(2)
    with col1:
        family = st.text_input("姓", value="")
    with col2:
        given = st.text_input("名", value="")
    submitted = st.form_submit_button("計算する")

if submitted and dict_name:
    table = load_dict(dict_name)
    res = calc(family, given, table)

    st.subheader("結果")
    st.metric("トップ（天格）", res["top"])
    st.metric("ハート（人格）", res["heart"])
    st.metric("フット（地格）", res["foot"])

    # サイド表示（3文字名の場合: 表面/本質 を併記）
    if "side_alt" in res:
        surface, essence = res["side_alt"]
        side_text = f'{res["side"]}（表面={surface}, 本質={essence}）'
    else:
        side_text = str(res["side"])
    st.metric("サイド（外格）", side_text)

    st.metric("オール（総格）", res["allv"])
