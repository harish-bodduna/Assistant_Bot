import sys
from pathlib import Path

import streamlit as st

# Ensure project root is on sys.path so `src` package imports work when run via streamlit
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.wrappers.qa_service import answer_question


st.set_page_config(page_title="1440 Bot", page_icon="🤖", layout="wide")
st.title("1440 Foods - Employee Virtual Assistant")

# Simple chat state
if "messages" not in st.session_state:
    st.session_state.messages = []


def add_message(role: str, content: str) -> None:
    st.session_state.messages.append({"role": role, "content": content})


# Render history
for msg in st.session_state.messages:
    with st.chat_message("user" if msg["role"] == "user" else "assistant"):
        st.markdown(msg["content"], unsafe_allow_html=True)

# Input box
prompt = st.chat_input("Ask a question about the manuals...")

if prompt:
    add_message("user", prompt)
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            res = answer_question(prompt)
            if res.get("ok"):
                reply = res.get("answer_markdown") or ""
            else:
                reply = f"Error: {res.get('message') or 'OpenAI call failed'}"

            if (not reply) or ("Request timed out" in reply):
                reply = "Still waiting on OpenAI… please retry in a moment."
            
            # Render markdown with image support
            # Streamlit's markdown can render images from URLs in ![alt](url) format
            st.markdown(reply, unsafe_allow_html=True)
            
            # Also try to render images directly if markdown doesn't work
            import re
            image_pattern = r'!\[([^\]]*)\]\((https?://[^\)]+)\)'
            images = re.findall(image_pattern, reply)
            if images:
                st.caption(f"Found {len(images)} image(s) in response")
                for alt_text, img_url in images[:5]:  # Limit to first 5 images
                    try:
                        st.image(img_url, caption=alt_text if alt_text else "Step image")
                    except Exception as e:
                        st.warning(f"Could not load image: {alt_text}")
            
            add_message("assistant", reply)

