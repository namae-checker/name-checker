# app_streamlit.py
import streamlit as st
import pandas as pd
import os
import glob

st.set_page_config(page_title="姓名判断（5格・霊数対応）", page_icon="🔮", layout="centered")

# ---------- 初回アクセス時は必ず空欄 ----------
if "first_load" not in st.session_state:
    st.session_state["family"] = ""   # 姓 初期値
    st.session_state["given"]  = ""   # 名 初期値
    st.session_state["first_load"] = False

# ---------- 辞書CSVのロード ----------
@st.cache_data
def load_kanji_master(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)

    # 画数カラムを推定（優先順位）
    stroke_candidates = ["strokes_old", "strokes", "strokes_std", "stroke", "画数", "strokes_new"]
    stroke_col = None
    for c in stroke_candidates:
        if c in df.columns:
            stroke_col = c
            break
    if stroke_col is None:
        # 最初の数値カラムを採用
        for c in df.columns:
            if pd.api.types.is_numeric_dtype(df[c]):
                stroke_col = c
                break
    if stroke_col is None:
        raise ValueError("画数カラムが見つかりませんでした（strokes_old 等の列を用意してください）。")

    # 文字列カラムを推定
    kanji_candidates = ["kanji", "字", "文字", "char"]
    kanji_col = None
    for kc in kanji_candidates:
        if kc in df.columns:
            kanji_col = kc
            break
    if kanji_col is None:
        # 最初の object 型カラムを採用
        obj_cols = [c for c in df.columns if df[c].dtype == object]
        if not obj_cols:
            raise ValueError("文字（kanji）列が見つかりませんでした。")
        kanji_col = obj_cols[0]

    out = df[[kanji_col, stroke_col]].rename(columns={kanji_col: "kanji", stroke_col: "strokes"})
    out["kanji"] = out["kanji"].astype(str)
    out = out[out["kanji"].str.len() == 1].copy()
    out["strokes"] = pd.to_numeric(out["strokes"], errors="coerce").fillna(0).astype(int)
    return out

def build_lookup(df: pd.DataFrame):
    m = dict(zip(df["kanji"], df["strokes"]))
    def lookup(ch: str) -> int:
        return int(m.get(ch, 0))  # 未登録は0
    return lookup

# ---------- 計算（霊数＆サイド二重表記） ----------
def calc_numbers(family: str, given: str, lookup_strokes):
    """
    ルール:
      1) 姓1文字 → 霊数1を頭につける（トップ/サイドに含める、総格には含めない）
      2) 名1文字 → 霊数1を末尾につける（フット/サイドに含める、総格には含めない）
      3) ハート（人格）= 実文字の『姓末＋名頭』
      4) サイド（本質）= 頭＋ケツ（霊数反映後）
      5) 名が3文字以上のとき、サイド（表面）= 頭＋（名の後ろ2文字の実画数）
         → 表示は「本質（表面）」
      6) 総格（オール）= 実文字だけ合計（霊数は含めない）
    """
    fam_actual = [lookup_strokes(c) for c in family]
    giv_actual = [lookup_strokes(c) for c in given]

    # 霊数付与（姓1→頭に1 / 名1→末尾に1）
    fam_for_top_side = fam_actual.copy()
    if len(family) == 1:
        fam_for_top_side = [1] + fam_for_top_side

    giv_for_foot_side = giv_actual.copy()
    if len(given) == 1:
        giv_for_foot_side = giv_for_foot_side + [1]

    # 五格
    top = sum(fam_for_top_side)
    heart = (fam_actual[-1] if fam_actual else 0) + (giv_actual[0] if giv_actual else 0)
    foot = sum(giv_for_foot_side)
    all_total = sum(fam_actual) + sum(giv_actual)

    # サイド（本質）
    head = fam_for_top_side[0] if fam_for_top_side else 0
    tail = giv_for_foot_side[-1] if giv_for_foot_side else 0
    side_base = head + tail

    # サイド（表面）: 名が3文字以上の時のみ（実文字の後ろ2文字）
    side_surface = None
    if len(given) >= 3:
        last_two = giv_actual[-2] + giv_actual[-1]
        side_surface = head + last_two

    # 表示用明細（霊数もわかるように並べる）
    detail_rows = []
    if len(family) == 1:
        detail_rows.append(("姓", "霊", 1))
    for ch, s in zip(family, fam_actual):
        detail_rows.append(("姓", ch, s))
    for ch, s in zip(given, giv_actual):
        detail_rows.append(("名", ch, s))
    if len(given) == 1:
        detail_rows.append(("名", "霊", 1))

    # 未登録文字（画数0）
    missing = {
        "family": [c for c, s in zip(family, fam_actual) if s == 0],
        "given":  [c for c, s in zip(given,  giv_actual) if s == 0],
    }

    return {
        "top": top,
        "heart": heart,
        "foot": foot,
        "side": side_base,
        "side_surface": side_surface,
        "all": all_total,
        "detail": detail_rows,
        "missing": missing,
    }

# ---------- UI ----------
st.title("姓名判断（5格）")
st.caption("霊数対応・サイド二重表記版")

# 辞書CSV（kanji_master*.csv）を自動列挙
csv_candidates = sorted(glob.glob("kanji_master*.csv"))
if not csv_candidates:
    st.error("kanji_master*.csv が見つかりません。リポジトリ直下に辞書CSVを置いてください。")
    st.stop()

dict_path = st.selectbox("使用する辞書を選択", csv_candidates, index=0)
df_dict = load_kanji_master(dict_path)
lookup = build_lookup(df_dict)
st.caption(f"辞書: {os.path.basename(dict_path)} / 登録文字: {len(df_dict):,}")

col1, col2 = st.columns(2)
with col1:
    family = st.text_input("姓", key="family", placeholder="例：田中", max_chars=10)
with col2:
    given  = st.text_input("名", key="given",  placeholder="例：太郎", max_chars=10)

# キャッシュ強制クリア（任意）
with st.expander("データの再読み込み（必要時のみ）"):
    if st.button("辞書を再読み込み"):
        st.cache_data.clear()
        st.success("辞書キャッシュをクリアしました。ページを再実行します。")
        st.rerun()

if st.button("計算する", type="primary"):
    if not family or not given:
        st.warning("姓と名を入力してください。")
    else:
        res = calc_numbers(family, given, lookup)

        st.subheader("結果")
        st.write(f"姓：{family}　名：{given}")

        # サイドの表示は 本質（表面）
        if res["side_surface"] is not None:
            side_text = f"{res['side']}（{res['side_surface']}）"
            side_note = "サイド（本質）は『頭＋ケツ』。サイド（表面）は『頭＋名の後ろ2文字（実画数）』。"
        else:
            side_text = str(res["side"])
            side_note = "サイドは『頭＋ケツ』で算出。"

        with st.container(border=True):
            st.metric("トップ（天格）", res["top"])
            st.metric("ハート（人格）", res["heart"])
            st.metric("フット（地格）", res["foot"])
            st.metric("サイド（外格）", side_text)
            st.metric("オール（総格）", res["all"])
        st.caption("※ 姓1文字→霊数『1』を頭に追加（トップ/サイドに反映、総格には含めない）。名1文字→霊数『1』を末尾に追加（フット/サイドに反映、総格には含めない）。")
        st.caption(side_note)

        # 文字ごとの内訳
        st.subheader("文字ごとの内訳")
        detail_df = pd.DataFrame(res["detail"], columns=["姓/名", "文字", "画数"])
        st.dataframe(detail_df, use_container_width=True, hide_index=True)

        # 未登録警告
        miss = res["missing"]["family"] + res["missing"]["given"]
        if miss:
            st.warning(f"辞書に未登録の文字があります: {'・'.join(miss)}（CSVの画数を追加してください）")
