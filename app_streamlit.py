# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from seimei_calc import load_dict, calc

st.set_page_config(page_title="姓名判断（5格）", layout="centered")
st.title("姓名判断（5格）")

with st.form("inputs"):
    col1, col2 = st.columns(2)
    with col1:
        family = st.text_input("姓", value="")
    with col2:
        given = st.text_input("名", value="")
    submitted = st.form_submit_button("計算する")

if submitted:
    try:
        table = load_dict()  # 固定: kanji_master_joyo.csv
        res = calc(family, given, table)

        st.subheader("結果")
        st.metric("トップ（天格）", res["トップ（天格）"])
        st.metric("ハート（人格）", res["ハート（人格）"])
        st.metric("フット（地格）", res["フット（地格）"])

        # サイドの表示：表面/本質の注記付き
        side = res.get("サイド", 0)
        side_surf = res.get("サイド（表面）", None)
        side_ess = res.get("サイド（本質）", None)
        if side_surf is not None and side_ess is not None and side_surf != side_ess:
            st.metric("サイド（外格）", f"{side}（表面={side_surf}, 本質={side_ess}）")
        else:
            st.metric("サイド（外格）", f"{side}")

        st.metric("オール（総格）", res["オール（総格）"])

        # 文字内訳（霊数の行も「内訳」として見える化）
        st.subheader("文字ごとの内訳（霊数は総格に含めません）")
        rows = []
        for kind, strokes, ch in res["内訳"]:
            rows.append({"区分": kind, "文字": ch, "画数": strokes})
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True)

    except Exception as e:
        st.error(f"エラーが発生しました: {e}")

# フッターメモ
with st.expander("計算ルール（要約）"):
    st.markdown(
        """
- 霊数は **総格に含めない** が、他の格には反映。
- 霊数の付与位置：姓が1文字 → **頭に+1**、名が1文字 → **末尾に+1**。
- サイド  
  - 名が3文字以上 → 表面= **姓1 + 名末2** / 本質= **姓1 + 名末1**  
  - 例外：姓・名ともに3文字以上 → **姓頭2 + 名末2**（表面=本質）  
  - 姓が3文字以上 → **姓頭2 + 名末1**（表面=本質）  
  - 姓1文字+名3文字 → 表面= **霊1 + 名末2** / 本質= **霊1 + 名末1**  
  - 名1文字 → ケツ霊数をサイドにも反映  
- 総格が **60** を超えた場合は **61→1** から再カウント。
        """
    )
