# -*- coding: utf-8 -*-
import streamlit as st
import os
import pandas as pd

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
    res = calc(family, given, table)

    st.subheader("結果")
    st.metric("トップ（天格）", res.get("top", 0))
    st.metric("ハート（人格）", res.get("heart", 0))
    st.metric("フット（地格）", res.get("foot", 0))

    side_val = res.get("side", 0)
    surface = res.get("side_surface")
    core = res.get("side_core")
    if surface is not None and core is not None:
        side_text = f"{side_val}（表面={surface}, 本質={core}）"
    else:
        side_text = str(side_val)
    st.metric("サイド（外格）", side_text)

    st.metric("オール（総格）", res.get("allv", 0))

    # 文字ごとの画数内訳
    bd = res.get("breakdown", [])
    if bd:
        df = pd.DataFrame(bd, columns=["区分", "文字", "画数"])
        st.subheader("文字ごとの内訳")
        st.table(df)
