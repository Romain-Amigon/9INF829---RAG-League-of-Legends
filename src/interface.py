import streamlit as st
from agent.main import setup_llm, setup_retriever, create_graph, run

st.set_page_config(page_title="LoL RAG Assistant", page_icon="🎮")

st.title("League of Legends RAG Assistant")

if "app" not in st.session_state:
    llm = setup_llm()
    retriever = setup_retriever(data_dir="data/rag", persist_dir="data/rag/vectors")
    st.session_state.app = create_graph(llm, retriever)

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
            final_response, final_reflections = run(st.session_state.app, prompt, thread_id="streamlit_session")
            
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
            message_placeholder.markdown(f"❌ Erreur lors de l'exécution : {str(e)}")