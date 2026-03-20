"""チャットUI"""

import streamlit as st

from src.search.flow import rag_flow

SAMPLE_QUESTIONS = [
    "ネジ999999の材質は？",
    "VPN接続の手順を教えて",
    "PCが重い",
    "有給休暇は何日もらえる？",
    "来月の株価は？",
    "ネジ999999と999998の違いは？",
]

st.title("エンタープライズRAG PoC")
st.caption("社内ドキュメントに基づいて質問に回答します")

# セッション状態で会話履歴を管理
if "messages" not in st.session_state:
    st.session_state.messages = []

# サンプル質問（サイドバーに常時表示）
with st.sidebar:
    st.markdown("**質問の例:**")
    for i, q in enumerate(SAMPLE_QUESTIONS):
        if st.button(q, key=f"sample_{i}", use_container_width=True):
            st.session_state.pending_query = q
            st.rerun()

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


def _handle_query(query: str):
    """質問を処理して会話履歴に追加する"""
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

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

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": result.answer,
            "sources": sources_data,
        }
    )


# サンプル質問のクリック処理
if "pending_query" in st.session_state:
    query = st.session_state.pop("pending_query")
    _handle_query(query)

# テキスト入力
if query := st.chat_input("質問を入力してください"):
    _handle_query(query)
