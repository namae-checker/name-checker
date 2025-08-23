# -*- coding: utf-8 -*-
import os
import csv
import streamlit as st

# seimei_calc の公開関数のみ import
from seimei_calc import load_dict, calc, strokes_of

# ---------------- UI ヘッダ ----------------
st.set_page_config(page_title="姓名判断（5格）", layout="centered")
st.title("姓名判断（5格）")

# ---------------- ヘルパ ----------------
@st.cache_data(show_spinner=False)
def list_dict_files() -> list[str]:
    files = [
        f for f in os.listdir(".")
        if f.startswith("kanji_master_") and f.endswith(".csv")
    ]
    files.sort()
    return files

@st.cache_data(show_spinner=False)
def load_table(path: str) -> dict:
    return load_dict(path)

def per_char_rows(family: str, given: str, table: dict):
    rows = []
    for kind, s in (("姓", family), ("名", given)):
        for ch in list(s):
            rows.append(
                {"区分": kind, "文字": ch, "画数": strokes_of(ch, table)}
            )
    return rows

# ---------------- 入力フォーム ----------------
dict_files = list_dict_files()
if not dict_files:
    st.error("kanji_master_*.csv が見つかりません。リポジトリ直下に置いてください。")
    st.stop()

with st.form("main_form", clear_on_submit=False):
    dict_name = st.selectbox("使用する辞書を選択", dict_files, index=0)
    col1, col2 = st.columns(2)
    with col1:
        family = st.text_input("姓", value="")
    with col2:
        given = st.text_input("名", value="")
    submitted = st.form_submit_button("計算する")

if not submitted or not dict_name:
    st.stop()

# ---------------- 計算 ----------------
table = load_table(dict_name)
res = calc(family, given, table)

# ---------------- 結果表示 ----------------
st.subheader("結果")

st.metric("トップ（天格）", res["トップ（天格）"])
st.metric("ハート（人格）", res["ハート（人格）"])
st.metric("フット（地格）", res["フット（地格）"])

side_text = f"{res['サイド（外格）']}  （表面={res['サイド_表面']}, 本質={res['サイド_本質']}）"
st.metric("サイド（外格）", side_text)

st.metric("オール（総格）", res["オール（総格）"])

# ---------------- 明細（文字ごとの内訳） ----------------
st.subheader("文字ごとの内訳")
rows = per_char_rows(family, given, table)
if rows:
    # 表示順: 区分 → 文字 → 画数
    st.dataframe(rows, use_container_width=True)
else:
    st.info("姓名を入力してください。")

# ---------------- 補足 ----------------
with st.expander("補足（仕組み）", expanded=False):
    st.markdown(
        """
- 画数は辞書（`strokes_old`）を基本に、**部首のカスタム画数**（`radicals_master_fixed.csv`）を
  **主部首**（`kanji_radicals_fixed.csv`）に対して差分加算して自動調整します。
- **文字個別の上書き**（`kanji_overrides.csv`）がある場合は、そちらを最優先で採用します。
- 霊数：「姓1文字→頭+1」「名1文字→ケツ+1」（いずれも**総格には含めません**）
- サイド（外格）：
  - 基本＝**頭（姓先頭） + ケツ（名末字）**
  - 名が3文字以上の場合、**（頭 + 名の末字）** を「本質」として計算し、**大きい方**を採用します。
        """
    )
