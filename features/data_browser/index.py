"""データブラウザ — Firestoreチャンクデータの閲覧"""

import json
import os
from datetime import datetime

import pandas as pd
import streamlit as st

from src.browse.exporter import export_collection

CACHE_DIR = "data_cache"
CSV_PATH = os.path.join(CACHE_DIR, "chunks.csv")
META_PATH = os.path.join(CACHE_DIR, "meta.json")

st.title("データブラウザ")
st.caption("Firestoreに格納されたチャンクデータを閲覧します")

# ダウンロードボタン
col1, col2 = st.columns([1, 3])
with col1:
    if st.button("📥 データをダウンロード"):
        with st.spinner("Firestoreからデータを取得中..."):
            count = export_collection(CACHE_DIR)
        st.success(f"{count}件のチャンクを取得しました")
        st.rerun()

with col2:
    if os.path.exists(META_PATH):
        with open(META_PATH, "r", encoding="utf-8") as f:
            meta = json.load(f)
        st.caption(f"最終取得: {meta['exported_at']} ({meta['count']}件)")
    else:
        st.caption("まだデータを取得していません")

st.divider()

# CSV表示
if not os.path.exists(CSV_PATH):
    st.info("「データをダウンロード」ボタンを押して、Firestoreからデータを取得してください。")
else:
    df = pd.read_csv(CSV_PATH)

    # フィルタ
    col_filter1, col_filter2 = st.columns(2)
    with col_filter1:
        categories = ["すべて"] + sorted(df["category"].unique().tolist())
        selected_category = st.selectbox("カテゴリ", categories)
    with col_filter2:
        security_levels = ["すべて"] + sorted(df["security_level"].unique().tolist())
        selected_security = st.selectbox("セキュリティレベル", security_levels)

    filtered = df
    if selected_category != "すべて":
        filtered = filtered[filtered["category"] == selected_category]
    if selected_security != "すべて":
        filtered = filtered[filtered["security_level"] == selected_security]

    st.subheader(f"チャンク一覧 ({len(filtered)}件)")

    # テーブル表示（contentは先頭80文字に truncate）
    display_df = filtered.copy()
    display_df["content_preview"] = display_df["content"].str[:80] + "..."
    display_cols = ["source_file", "chunk_index", "category", "security_level", "content_preview"]

    event = st.dataframe(
        display_df[display_cols],
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
    )

    # 行選択で詳細表示
    if event.selection and event.selection.rows:
        selected_idx = event.selection.rows[0]
        row = filtered.iloc[selected_idx]

        st.subheader("チャンク詳細")
        st.text(f"ソース: {row['source_file']}  チャンク: #{row['chunk_index']}")
        st.text(f"カテゴリ: {row['category']}  セキュリティ: {row['security_level']}")
        st.text(f"許可グループ: {row['allowed_groups']}")
        st.divider()
        st.markdown(row["content"])
