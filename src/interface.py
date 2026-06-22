import streamlit as st
import asyncio
import threading

st.set_page_config(page_title="LoL Multi-Agents Assistant", page_icon="🎮")
st.title("League of Legends — Multi-Agents Assistant")

@st.cache_resource
def get_persistent_loop():
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()
    return loop

def run_async(coro):
    loop = get_persistent_loop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result()

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "reflections" in msg and msg["reflections"]:
            with st.expander("Traces et décisions des agents"):
                for r in msg["reflections"]:
                    st.text(r)

prompt = st.chat_input("Ask your question about League of Legends...")

if prompt:
    from agent.main import get_response

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("⏳ Routage et analyse en cours...")
        try:
            final_response, final_reflections = run_async(
                get_response(prompt, thread_id="streamlit_session")
            )

            message_placeholder.markdown(final_response)
            if final_reflections:
                with st.expander("Traces et décisions des agents"):
                    for r in final_reflections:
                        st.text(r)
            st.session_state.messages.append({
                "role": "assistant",
                "content": final_response,
                "reflections": final_reflections,
            })
        except Exception as e:
            import traceback
            message_placeholder.markdown(f"❌ Erreur : {str(e)}")
            st.error(traceback.format_exc())