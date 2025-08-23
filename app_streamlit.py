# -*- coding: utf-8 -*-
import streamlit as st
import os
from seimei_calc import load_dict, calc

st.set_page_config(page_title="姓名判断（5格）", layout="centered")

# ===== UI（選択の詳細を結果に出さない・初期値は空） =====
st.title("姓名判断（5格）")

dict_files = [f for f in os.listdir(".") if f.startswith("kanji_master_") and f.endswith(".csv")]
dict_files.sort()
dict_name = st.selectbox("使用する辞書を選択", dict_files, index=0 if dict_files else None)

col1, col2 = st.columns(2)
with col1:
    family = st.text_input("姓", value="")
with col2:
    given = st.text_input("名", value="")

recalc = st.button("計算する")

# ===== 計算 =====
if recalc and dict_name and (family or given):
    table = load_dict(dict_name)
    res = calc(family, given, table)

    st.subheader("結果")
    c = st.container()
    c.metric("トップ（天格）", res["トップ（天格）"])
    c.metric("ハート（人格）", res["ハート（人格）"])
    c.metric("フット（地格）", res["フット（地格）"])
    c.metric("サイド（外格）", res["サイド（外格）"])
    c.metric("オール（総格）", res["オール（総格）"])
