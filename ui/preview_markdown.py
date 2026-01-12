import streamlit as st
from pathlib import Path


st.title("1440 Markdown + SAS Preview")

default_md = Path("markdown_exports/External_SharePoint_access/markdown.md")
md_path = st.text_input("Markdown path", value=str(default_md))

if st.button("Load markdown"):
    path = Path(md_path)
    if not path.exists():
        st.error(f"File not found: {path}")
    else:
        md = path.read_text(encoding="utf-8")
        st.markdown(md)
        st.caption("Images are fetched via Azure SAS; ensure they remain valid.")

