"""エンタープライズRAG PoC — ナビゲーションハブ"""

import sys
from pathlib import Path

import streamlit as st

# sys.path にプロジェクトルートを追加
sys.path.insert(0, str(Path(__file__).resolve().parent))

st.set_page_config(
    page_title="エンタープライズRAG PoC",
    page_icon="🔍",
    layout="wide",
)

chat_page = st.Page("features/chat/index.py", title="チャット", icon="💬", url_path="chat")
browser_page = st.Page("features/data_browser/index.py", title="データブラウザ", icon="📊", url_path="data-browser")

nav = st.navigation([chat_page, browser_page])
nav.run()
