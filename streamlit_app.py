import sys
import os
from pathlib import Path
import traceback
import streamlit as st

# Initialize Page must be the FIRST streamlit command
st.set_page_config(
    page_title="Grow RAG | Facts-Only Assistant",
    page_icon="📈",
    layout="wide"
)

# Global error catcher for initialization
try:
    # Add src to PYTHONPATH so we can import mf_faq
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

    # Load Streamlit Secrets if available
    if hasattr(st, "secrets") and "GROQ_API_KEY" in st.secrets:
        os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]

    # Auto-build the knowledge base if the index doesn't exist
    index_path = Path("data/index/vector.faiss")
    if not index_path.exists():
        st.info("First-time setup: Initializing Knowledge Base and downloading embeddings... This may take a minute.")
        from mf_faq.ingestion.pipeline.service import Pipeline
        Pipeline().refresh()
        st.success("Knowledge Base initialized! Ready to chat.")

    from mf_faq.orchestrator.service import OrchestratorService

    # Initialize Orchestrator once
    @st.cache_resource
    def get_orchestrator():
        return OrchestratorService()

    orchestrator = get_orchestrator()

except Exception as e:
    st.error("Application Failed to Initialize. Please check the logs or screenshot this error:")
    st.code(traceback.format_exc())
    st.stop()

# Initialize Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar
with st.sidebar:
    st.title("Grow RAG")
    st.caption("Professional Finance Assistant")
    
    if st.button("➕ CLEAR CHAT", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.markdown("### Example Questions")
    
    examples = [
        "What is the expense ratio of HDFC Mid Cap Fund?",
        "What is the exit load of HDFC Equity Fund?"
    ]
    
    for ex in examples:
        if st.button(ex, help="Click to ask"):
            st.session_state.messages.append({"role": "user", "content": ex})
            st.rerun()

# Main Chat Area
st.title("Grow RAG Chatbot")
st.markdown("*Instantly query verified documents for listed HDFC schemes.*")

# Display chat messages from history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Accept user input
if prompt := st.chat_input("Ask a factual question about listed HDFC schemes..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)

    # Display assistant response with a spinner
    with st.chat_message("assistant"):
        with st.spinner("Searching verified sources..."):
            try:
                # Call orchestrator.ask() instead of .process()
                response = orchestrator.ask(prompt)
                st.markdown(response)
                # Add assistant response to chat history
                st.session_state.messages.append({"role": "assistant", "content": response})
            except Exception as e:
                st.error("Sorry, I encountered a system error.")
                st.exception(e)
