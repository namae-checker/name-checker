# -*- coding: utf-8 -*-
import os
import csv
import streamlit as st

# seimei_calc から辞書読み込み関数を安全に import
try:
    from seimei_calc import load_dict as _load_dict
except Exception:
    # 互換用（古い版で _load_dict の場合）
    from seimei_calc import _load_dict
from seimei_calc import calc


st.set_page_config(page_title="姓名判断（5格）", layout="centered")
st.title("姓名判断（5格）")

# 利用可能な辞書ファイルを収集
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

def _pick(res: dict, jp_key: str, en_key: str, default=0):
    """日本語キー / 英語キーの両対応で値を取得"""
    if jp_key in res:
        return res[jp_key]
    if en_key in res:
        return res[en_key]
    return default

if submitted and dict_name:
    # 辞書ロード
    table = _load_dict(dict_name)

    # 計算
    res = calc(family, given, table)

    # ---- 両キー対応で値を取得 ----
    top   = _pick(res, "トップ（天格）", "top")
    heart = _pick(res, "ハート（人格）", "heart")
    foot  = _pick(res, "フット（地格）", "foot")
    side  = _pick(res, "サイド（外格）", "side")
    allv  = _pick(res, "オール（総格）", "allv")

    side_surface = res.get("サイド_表面", res.get("side_surface"))
    side_core    = res.get("サイド_本質", res.get("side_core"))

    st.subheader("結果")
    st.metric("トップ（天格）", top)
    st.metric("ハート（人格）", heart)
    st.metric("フット（地格）", foot)

    if side_surface is not None and side_core is not None:
        side_text = f"{side}（表面={side_surface}, 本質={side_core}）"
    else:
        side_text = str(side)
    st.metric("サイド（外格）", side_text)

    st.metric("オール（総格）", allv)

    # 文字ごとの内訳（表示用）
    def _breakdown(family: str, given: str):
        rows = []
        for ch in family:
            rows.append(("姓", ch, table.get(ch, 0)))
        for ch in given:
            rows.append(("名", ch, table.get(ch, 0)))
        return rows

    rows = _breakdown(family, given)
    if rows:
        import pandas as pd
        df = pd.DataFrame(rows, columns=["区分", "文字", "画数"])
        st.subheader("文字ごとの内訳")
        st.dataframe(df, use_container_width=True)
