# -*- coding: utf-8 -*-
import os
import io
import traceback

# 重要: GUIバックエンドを強制（クラウド/サーバでも安全）
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import streamlit as st
import pandas as pd

from seimei_calc import calc_full

# 日本語フォント（あるものが使われる）
matplotlib.rcParams["font.family"] = [
    "IPAPGothic", "Noto Sans CJK JP", "Hiragino Sans",
    "Yu Gothic", "Meiryo", "TakaoGothic", "DejaVu Sans"
]


def preflight() -> list[str]:
    """
    代表的な落とし穴を事前チェックして、警告リストを返す。
    """
    warns = []

    # CSVの所在チェック
    root = os.path.dirname(__file__)
    csv_base = os.path.join(root, "kanji_master_joyo.csv")
    if not os.path.exists(csv_base):
        warns.append("辞書ファイル `kanji_master_joyo.csv` が見つかりません。レポジトリ直下に置いてください。")

    # 追加上書きは任意
    csv_over = os.path.join(root, "kanji_overrides.csv")
    if not os.path.exists(csv_over):
        warns.append("`kanji_overrides.csv` は任意ですが、無ければこの警告は無視してOKです。")

    # 依存の確認（importできたか）
    try:
        import numpy  # noqa: F401
        import pandas  # noqa: F401
        import matplotlib  # noqa: F401
    except Exception as e:
        warns.append(f"依存ライブラリの読み込みに失敗: {e}")

    return warns


def draw_bracket_figure(
    family: str, given: str, parts: dict,
    family_labels: list[str], given_labels: list[str],
):
    """
    読みやすい固定レイアウトのブラケット図（Aggバックエンド）
    """
    fig = plt.figure(figsize=(9, 5), dpi=180)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_axis_off()

    # タイトル
    ax.text(0.02, 0.93, f"{family}{given}　さんの姓名判断結果", fontsize=16, weight="bold")
    ax.text(0.02, 0.89, f"オール {parts['allv']}", fontsize=12)
    if parts.get("all_expr"):
        ax.text(0.02, 0.865, parts["all_expr"], fontsize=11)

    # ブラケット
    x0 = 0.12
    y0 = 0.70
    h = 0.38

    ax.plot([x0, x0], [y0 - h, y0], color="black", lw=1.6)
    ax.plot([x0, x0 + 0.03], [y0, y0], color="black", lw=1.6)
    ax.plot([x0, x0 + 0.03], [y0 - h, y0 - h], color="black", lw=1.6)

    # 4行に整形（姓2+名2を優先。足りないところは空文字）
    lines = ["", "", "", ""]
    if family_labels:
        lines[0] = family_labels[0]
    if len(family_labels) >= 2:
        lines[1] = family_labels[1]
    elif given_labels:
        lines[1] = given_labels[0]
    if len(given_labels) >= 2:
        lines[2] = given_labels[-2]
    if len(given_labels) >= 1:
        lines[3] = given_labels[-1]

    line_y = [y0 - i * (h / 4) for i in range(4)]
    for yy, s in zip(line_y, lines):
        ax.text(x0 - 0.035, yy - 0.005, s, ha="right", va="center", fontsize=12)

    xr = x0 + 0.06
    ax.text(xr, line_y[0] + 0.02, f"{parts['top']} → トップ・・・血統", fontsize=11)
    ax.text(xr, line_y[1] + 0.02, f"{parts['heart']} → ハート・・・性格・愛情", fontsize=11)
    ax.text(xr, line_y[2] + 0.02, f"{parts['foot']} → フット・・・恋愛", fontsize=11)

    # サイド
    ax.text(0.16, (line_y[1] + line_y[2]) / 2, f"職業・・・サイド ← {parts['side']}", fontsize=11, va="center")
    ax.text(0.60, 0.50, f"サイド：表面={parts['side_face']}、本質={parts['side_core']}", fontsize=10, ha="left")

    ax.plot([0.12, 0.86], [0.20, 0.20], color="black", lw=1.2)
    ax.text(0.47, 0.17, f"{parts['allv']}  →  オール・・・全体", fontsize=12, ha="center")

    return fig


def render_metric(label: str, value: int | str, sub: str | None = None):
    html = f"""
    <div style="display:flex;flex-direction:column;gap:6px;padding:10px 12px;border:1px solid #ddd;border-radius:8px;">
      <div style="font-size:13px;color:#666;">{label}</div>
      <div style="font-size:40px;font-weight:700;line-height:1.0;">{value}</div>
      {f'<div style="font-size:13px;color:#555;word-break:break-all;">{sub}</div>' if sub else ''}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


# =========== UI ===========
st.set_page_config(page_title="姓名判断（5格）", layout="wide")
st.title("姓名判断（5格）")

# 事前チェック
warns = preflight()
if warns:
    with st.expander("環境チェック（必要なら確認してください）", expanded=False):
        for w in warns:
            st.write("•", w)

with st.form("main"):
    colA, colB = st.columns(2)
    with colA:
        family = st.text_input("姓", value="三野原")
    with colB:
        given = st.text_input("名", value="正章")
    submitted = st.form_submit_button("計算する")

if not submitted:
    st.info("姓と名を入力して「計算する」を押してください。辞書は `kanji_master_joyo.csv` を固定で使用し、`kanji_overrides.csv` があれば最優先で上書きされます。")
    st.stop()

# すべての例外をキャッチして、画面に詳細を表示
try:
    res = calc_full(family, given)

    cols = st.columns(4)
    with cols[0]:
        render_metric("トップ（天格）", res["top"], sub=res["top_expr"])
    with cols[1]:
        render_metric("ハート（人格）", res["heart"], sub=res["heart_expr"])
    with cols[2]:
        render_metric("フット（地格）", res["foot"], sub=res["foot_expr"])
    with cols[3]:
        sub = f"（表面={res['side_face']}、本質={res['side_core']}）"
        render_metric("サイド（外格）", res["side"], sub=sub)

    st.divider()
    render_metric("オール（総格）", res["allv"], sub=res["all_expr"])

    st.subheader("文字ごとの内訳（霊数も表示）")
    df = pd.DataFrame(res["table_rows"], columns=["区分", "文字", "画数"])
    st.dataframe(df, hide_index=True, use_container_width=True)

    st.subheader("図解（ブラケット図）")
    fig = draw_bracket_figure(family, given, res, res["family_labels"], res["given_labels"])
    st.pyplot(fig)

except Exception as e:
    st.error("アプリ内で例外が発生しました。詳細ログを下に表示します。")
    buf = io.StringIO()
    traceback.print_exc(file=buf)
    st.code(buf.getvalue(), language="text")
