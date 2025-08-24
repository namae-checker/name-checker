# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd

from seimei_calc import (
    load_dict,
    calc,
    normalize_name,
    stroke_for_char,
)

st.set_page_config(page_title="姓名判断", layout="centered")
st.title("姓名判断（5格）")

def fmt_expr(terms, total):
    """
    terms: List[Tuple[str, int]] を「字（画数）」の足し算式に整形
    例: [("三",3),("野",11),("原",10)] -> "三（3）+野（11）+原（10）＝24"
    """
    lhs = " + ".join([f"{k}（{v}）" for k, v in terms])
    return f"{lhs} ＝ {total}"

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
        # まず既存ロジックで最終値を算出
        res = calc(family, given, table)

        # 計算式を作るため、ここでもう一度パーツ別に構築
        f = normalize_name(family)
        g = normalize_name(given)
        fchars = list(f)
        gchars = list(g)
        fn, gn = len(fchars), len(gchars)

        rei_head = 1 if fn == 1 else 0
        rei_tail = 1 if gn == 1 else 0

        def term_char_list(chars):
            return [(ch, stroke_for_char(ch, table)) for ch in chars]

        # トップ（天格）: 姓の合計 + 頭霊数
        top_terms = []
        if rei_head:
            top_terms.append(("霊", 1))
        top_terms += term_char_list(fchars)

        # ハート（人格）: 姓末字 + 名先頭字
        heart_terms = []
        if fn > 0 and gn > 0:
            heart_terms = [
                (fchars[-1], stroke_for_char(fchars[-1], table)),
                (gchars[0], stroke_for_char(gchars[0], table)),
            ]

        # フット（地格）: 名の合計 + ケツ霊数
        foot_terms = term_char_list(gchars)
        if rei_tail:
            foot_terms += [("霊", 1)]

        # サイド（外格）: 規則によって表面式と本質式を作る
        side_surface_expr = None
        side_essence_expr = None

        # 例外：姓・名ともに3文字以上 → 姓頭2 + 名末2（表面=本質）
        if fn >= 3 and gn >= 3:
            t = term_char_list(fchars[:2]) + term_char_list(gchars[-2:])
            side_surface_expr = fmt_expr(t, res["サイド"])  # 同値
            side_essence_expr = fmt_expr(t, res["サイド"])

        # 姓が3文字以上 → 姓頭2 + 名末1（表面=本質）
        elif fn >= 3 and gn >= 1:
            t = term_char_list(fchars[:2]) + term_char_list(gchars[-1:])
            if gn == 1 and rei_tail:
                t += [("霊", 1)]
            side_surface_expr = fmt_expr(t, res["サイド"])
            side_essence_expr = fmt_expr(t, res["サイド"])

        else:
            # その他：名が3文字以上 → 表面: 姓1 + 名末2 / 本質: 姓1 + 名末1
            # 姓1文字のときの「頭1」は霊数1
            head_1 = [("霊", 1)] if fn == 1 else (term_char_list(fchars[:1]) if fn >= 1 else [])

            if gn >= 3:
                essence_terms = head_1 + term_char_list(gchars[-1:])
                surface_terms = head_1 + term_char_list(gchars[-2:])
                side_essence_expr = fmt_expr(essence_terms, res["サイド（本質）"])
                side_surface_expr = fmt_expr(surface_terms, res["サイド（表面）"])

            elif gn == 2:
                essence_terms = head_1 + term_char_list(gchars[-1:])
                side_essence_expr = fmt_expr(essence_terms, res["サイド（本質）"])
                side_surface_expr = side_essence_expr

            elif gn == 1:
                essence_terms = head_1 + term_char_list(gchars[-1:])
                if rei_tail:
                    essence_terms += [("霊", 1)]
                side_essence_expr = fmt_expr(essence_terms, res["サイド（本質）"])
                side_surface_expr = side_essence_expr

            else:
                essence_terms = head_1
                side_essence_expr = fmt_expr(essence_terms, res["サイド（本質）"])
                side_surface_expr = side_essence_expr

        # オール（総格）: 姓+名（霊数は含めない）
        all_terms = term_char_list(fchars) + term_char_list(gchars)

        # ====== 画面表示 ======
        st.subheader("結果（値）")
        st.metric("トップ（天格）", res["トップ（天格）"])
        st.metric("ハート（人格）", res["ハート（人格）"])
        st.metric("フット（地格）", res["フット（地格）"])

        side = res.get("サイド", 0)
        side_surf = res.get("サイド（表面）", None)
        side_ess = res.get("サイド（本質）", None)
        if side_surf is not None and side_ess is not None and side_surf != side_ess:
            st.metric("サイド（外格）", f"{side}（表面={side_surf}, 本質={side_ess}）")
        else:
            st.metric("サイド（外格）", f"{side}")

        st.metric("オール（総格）", res["オール（総格）"])

        st.subheader("結果（計算式）")
        st.markdown(f"**トップ** ＝ {fmt_expr(top_terms, res['トップ（天格）'])}")
        if heart_terms:
            st.markdown(f"**ハート** ＝ {fmt_expr(heart_terms, res['ハート（人格）'])}")
        else:
            st.markdown("**ハート** ＝ （計算対象の字がありません）")

        st.markdown(f"**フット** ＝ {fmt_expr(foot_terms, res['フット（地格）'])}")

        if side_surface_expr and side_essence_expr and side_surface_expr != side_essence_expr:
            st.markdown(f"**サイド（表面）** ＝ {side_surface_expr}")
            st.markdown(f"**サイド（本質）** ＝ {side_essence_expr}")
        else:
            # 同じ式の場合は1行で
            st.markdown(f"**サイド** ＝ {side_essence_expr or side_surface_expr}")

        st.markdown(f"**オール** ＝ {fmt_expr(all_terms, res['オール（総格）'])}")

        # 文字内訳（霊数も列に出すが、オールには含めない旨を注記）
        st.subheader("文字ごとの内訳（霊数は総格に含めません）")
        rows = []
        for kind, strokes, ch in res["内訳"]:
            rows.append({"区分": kind, "文字": ch, "画数": strokes})
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True)

    except Exception as e:
        st.error(f"エラーが発生しました: {e}")

