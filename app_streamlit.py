# -*- coding: utf-8 -*-
import os
import streamlit as st
from seimei_calc import calc, _load_dict

st.set_page_config(page_title="姓名判断", layout="centered")
st.title("姓名判断")

# 利用可能な辞書ファイルをプルダウンに
dict_files = [f for f in os.listdir(".") if f.startswith("kanji_master_") and f.endswith(".csv")]
dict_files.sort()

with st.form("main_form"):
    dict_name = st.selectbox("使用する辞書を選択", dict_files, index=0 if dict_files else 0)
    col1, col2 = st.columns(2)
    with col1:
        family = st.text_input("姓", value="")
    with col2:
        given = st.text_input("名", value="")
    submitted = st.form_submit_button("計算する")

if submitted and dict_name:
    table = _load_dict(dict_name)
    res = calc(family, given, table)

    st.subheader("結果")
    st.metric("トップ（天格）", res["top"])
    st.metric("ハート（人格）", res["heart"])
    st.metric("フット（地格）", res["foot"])

    # サイド：表面/本質の内訳を併記
    side_text = str(res["side"])
    face = res.get("side_face")
    real = res.get("side_real")
    if face is not None and real is not None:
        side_text += f"（表面={face}, 本質={real}）"
    st.metric("サイド（外格）", side_text)

    st.metric("オール（総格）", res["allv"])


