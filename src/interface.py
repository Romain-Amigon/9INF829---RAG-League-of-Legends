import streamlit as st
import asyncio
import nest_asyncio
from agent.main import get_response

nest_asyncio.apply()

st.set_page_config(page_title="LoL RAG Assistant", page_icon="🎮")
st.title("League of Legends RAG Assistant")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "reflections" in msg and msg["reflections"]:
            with st.expander("Traces et Réflexions du modèle"):
                for r in msg["reflections"]:
                    st.text(r)

prompt = st.chat_input("Posez votre question sur League of Legends...")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("⏳ Analyse en cours...")
        
        try:
            loop = asyncio.get_event_loop()
            final_response, final_reflections = loop.run_until_complete(
                get_response(prompt, thread_id="streamlit_session")
            )
            
            message_placeholder.markdown(final_response)
            
            if final_reflections:
                with st.expander("Traces et Réflexions du modèle"):
                    for r in final_reflections:
                        st.text(r)
                        
            st.session_state.messages.append({
                "role": "assistant",
                "content": final_response,
                "reflections": final_reflections
            })
            
        except Exception as e:
            message_placeholder.markdown(f"❌ Execution error: {str(e)}")