# -*- coding: utf-8 -*-
import os
import csv
from typing import Dict, List, Tuple

import streamlit as st
import pandas as pd

# ---- seimei_calc から計算関数と辞書ローダを取り込む ---------------------------------
# どちらの命名でも動くようにフォールバックを用意
try:
    from seimei_calc import calc, load_dict as _load_dict
except ImportError:
    from seimei_calc import calc, _load_dict  # type: ignore


# ---- 画面基本設定 --------------------------------------------------------------------
st.set_page_config(page_title="姓名判断（5格）", layout="centered")
st.title("姓名判断（5格）")

# ---- 利用可能な辞書ファイルを列挙 ----------------------------------------------------
def list_dict_files() -> List[str]:
    files = []
    for f in os.listdir("."):
        if f.startswith("kanji_master_") and f.endswith(".csv"):
            files.append(f)
    files.sort()
    return files


# ---- オーバーライド（1文字ごとの強制画数）を読み込み ----------------------------------
def load_overrides(path: str = "kanji_overrides.csv") -> Dict[str, int]:
    data: Dict[str, int] = {}
    if not os.path.exists(path):
        return data
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ch = (row.get("char") or "").strip()
                stv = (row.get("strokes") or "").strip()
                if not ch or not stv:
                    continue
                try:
                    data[ch] = int(stv)
                except ValueError:
                    pass
    except Exception:
        # 読み込み失敗時は空のまま返す
        return {}
    return data


# ---- 1文字の画数（オーバーライド優先→辞書） ------------------------------------------
def stroke_for_char(ch: str, table: Dict[str, int], overrides: Dict[str, int]) -> int:
    if ch in overrides:
        return overrides[ch]
    return table.get(ch, 0)


# ---- 入力フォーム ---------------------------------------------------------------------
dict_files = list_dict_files()
with st.form("name_form"):
    dict_name = st.selectbox("使用する辞書を選択", dict_files, index=0 if dict_files else -1)
    col1, col2 = st.columns(2)
    with col1:
        family = st.text_input("姓", value="")
    with col2:
        given = st.text_input("名", value="")
    submitted = st.form_submit_button("計算する")

# ---- 計算実行 ------------------------------------------------------------------------
if submitted and dict_name:
    # 画数辞書 & オーバーライドをロード
    table = _load_dict(dict_name)
    overrides = load_overrides()

    # 5格計算（霊数ルール・サイドの表面/本質などは seimei_calc.calc 側に実装）
    res = calc(family, given, table)

    # ---- 集計の表示（サイドは表面/本質を併記） --------------------------------------
    st.subheader("結果")
    top = res.get("トップ（天格）", 0)
    heart = res.get("ハート（人格）", 0)
    foot = res.get("フット（地格）", 0)
    side_main = res.get("サイド（外格・本質）", 0)
    side_surface = res.get("サイド（外格・表面）")
    allv = res.get("オール（総格）", 0)

    st.metric("トップ（天格）", top)
    st.metric("ハート（人格）", heart)
    st.metric("フット（地格）", foot)

    if side_surface is not None:
        # 例：21（表面=19, 本質=21）
        st.metric("サイド（外格）", f"{side_main}（表面={side_surface}, 本質={side_main}）")
    else:
        st.metric("サイド（外格）", side_main)

    st.metric("オール（総格）", allv)

    # ---- 文字ごとの内訳（霊数は表示に含めない） -------------------------------------
    # 画面に示す内訳は「姓/名の各文字とその画数」。霊数は明細に含めない。
    rows: List[Tuple[str, str, int]] = []
    for ch in family:
        rows.append(("姓", ch, stroke_for_char(ch, table, overrides)))
    for ch in given:
        rows.append(("名", ch, stroke_for_char(ch, table, overrides)))

    if rows:
        st.subheader("文字ごとの内訳（霊数は表示に含めません）")
        df = pd.DataFrame(rows, columns=["区分", "文字", "画数"])
        st.dataframe(df, hide_index=True, use_container_width=True)

else:
    # 初期状態や辞書未選択時の注意
    if not dict_files:
        st.info("kanji_master_*.csv の辞書ファイルが見つかりませんでした。リポジトリに追加してください。")
    else:
        st.caption("姓と名を入力して「計算する」を押してください。")
