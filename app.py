"""Streamlit チャットUI for RAG PoC"""

import streamlit as st

# sys.path にプロジェクトルートを追加
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.search.flow import rag_flow

st.set_page_config(
    page_title="エンタープライズRAG PoC",
    page_icon="🔍",
    layout="wide",
)

st.title("エンタープライズRAG PoC")
st.caption("社内ドキュメントに基づいて質問に回答します")

# セッション状態で会話履歴を管理
if "messages" not in st.session_state:
    st.session_state.messages = []

# 会話履歴を表示
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and msg.get("sources"):
            with st.expander(f"参照ソース ({len(msg['sources'])}件)"):
                for src in msg["sources"]:
                    st.text(
                        f"📄 {src['source_file']}#{src['chunk_index']}  "
                        f"score={src['score']:.3f}"
                    )

# 質問入力
if query := st.chat_input("質問を入力してください"):
    # ユーザーメッセージを表示・保存
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    # RAG Flow 実行
    with st.chat_message("assistant"):
        with st.spinner("検索・回答生成中..."):
            result = rag_flow(query)

        st.markdown(result.answer)

        sources_data = [
            {
                "source_file": s.source_file,
                "chunk_index": s.chunk_index,
                "score": s.score,
            }
            for s in result.reranked_sources
        ]

        if sources_data:
            with st.expander(f"参照ソース ({len(sources_data)}件)"):
                for src in sources_data:
                    st.text(
                        f"📄 {src['source_file']}#{src['chunk_index']}  "
                        f"score={src['score']:.3f}"
                    )

    # アシスタントメッセージを保存
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": result.answer,
            "sources": sources_data,
        }
    )
