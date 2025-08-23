# -*- coding: utf-8 -*-
import streamlit as st
import os
from seimei_calc import load_dict, calc

st.set_page_config(page_title="姓名判断（5格）", layout="centered")
st.title("姓名判断（5格）")

dict_files = [f for f in os.listdir(".") if f.startswith("kanji_master_") and f.endswith(".csv")]
dict_files.sort()

with st.form("main_form"):
    dict_name = st.selectbox("使用する辞書を選択", dict_files, index=0 if dict_files else None)
    col1, col2 = st.columns(2)
    with col1:
        family = st.text_input("姓", value="")
    with col2:
        given = st.text_input("名", value="")
    submitted = st.form_submit_button("計算する")

if submitted and dict_name:
    table = load_dict(dict_name)
    res = calc(args.family, args.given, table)

side_text = str(res["side"])
if res.get("side_alt"):
    side_text = f"{res['サイド（外格）']}（表面={res['サイド（外格 表面）']}, 本質={res['サイド（外格 本質）']}）"

st.subheader("結果")
st.metric("トップ（天格）", res["top"])
st.metric("ハート（人格）", res["heart"])
st.metric("フット（地格）", res["foot"])
st.metric("サイド（外格）", side_text)
st.metric("オール（総格）", res["allv"])

