# app_streamlit.py
import csv, unicodedata, os, streamlit as st

VARIANT_MAP = {"髙":"高","﨑":"崎","邊":"辺","邉":"辺"}
REPEAT_MARK = "々"

def z2h_digits(s: str) -> str:
    trans = {ord(c): ord('0')+i for i, c in enumerate('０１２３４５６７８９')}
    return s.translate(trans)

def normalize_name(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    out = []
    for ch in s:
        ch = VARIANT_MAP.get(ch, ch)
        if ch == REPEAT_MARK and out:
            ch = out[-1]
        out.append(ch)
    return "".join(out)

@st.cache_data
def load_table(csv_path: str) -> dict:
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        d = {}
        for row in r:
            k = (row.get("kanji") or "").strip()
            v = (row.get("strokes_old") or "").strip()
            v = z2h_digits(v)
            if not k: continue
            try: d[k] = int(v)
            except: d[k] = 0
        return d

def sum_strokes(s: str, tbl: dict) -> int:
    return sum(tbl.get(ch, 0) for ch in s)

def calc(family: str, given: str, tbl: dict):
    f = normalize_name(family)
    g = normalize_name(given)
    top  = sum_strokes(f, tbl)
    foot = sum_strokes(g, tbl)
    heart = (tbl.get(f[-1],0)+tbl.get(g[0],0)) if (f and g) else (top+foot)
    allv = top + foot
    side = max(allv - heart, 0)
    return f,g,top,heart,foot,side,allv

st.set_page_config(page_title="姓名判断（5格）", page_icon="🔢", layout="centered")
st.title("姓名判断（5格）")

# 辞書の選択
candidates = []
for f in ["kanji_master_custom.csv","kanji_master_joyo.csv","kanji_master_cultural_affairs.csv"]:
    if os.path.exists(f): candidates.append(f)
if not candidates:
    st.error("このフォルダに漢字マスタCSVが見つかりません。")
    st.stop()

csv_path = st.selectbox("使用する辞書を選択", candidates, index=0, format_func=lambda x: f"{x}（{'カスタム' if 'custom' in x else '常用' if 'joyo' in x else '文化庁'}）")
tbl = load_table(csv_path)
st.caption(f"辞書: {csv_path} / 登録文字: {len(tbl)}")

# 入力
col1, col2 = st.columns(2)
family = col1.text_input("姓", "田中")
given  = col2.text_input("名", "太郎")

if st.button("計算する", type="primary"):
    f,g,top,heart,foot,side,allv = calc(family, given, tbl)
    st.subheader("結果")
    st.write(f"**姓**：{f}　**名**：{g}")
    st.metric("トップ（天格）", top)
    st.metric("ハート（人格）", heart)
    st.metric("フット（地格）", foot)
    st.metric("サイド（外格）", side)
    st.metric("オール（総格）", allv)

    st.markdown("### 文字ごとの画数")
    st.table(
        [{"区分":"姓","文字":ch,"画数":tbl.get(ch,0)} for ch in f] +
        [{"区分":"名","文字":ch,"画数":tbl.get(ch,0)} for ch in g]
    )

st.markdown("---")
st.caption("※ 画数が0になる文字は辞書に未登録です。CSVで `strokes_old` を修正してください。")
