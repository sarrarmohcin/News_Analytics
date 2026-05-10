import streamlit as st
from elasticsearch import Elasticsearch


# connect to Elasticsearch
es_client = Elasticsearch(
    "http://elasticsearch:9200",
    verify_certs=False
)
if es_client.ping():
    st.session_state.es_client = es_client 
else:
    st.error("✗ Failed to connect to Elasticsearch")


st.set_page_config(
    layout="wide"
)

# --- PAGE SETUP ---
dashboard = st.Page(
    "pages/dashboard.py",
    title="Dashboard",
    icon=":material/dashboard:",
    default=True,
)
sources = st.Page(
    "pages/sources.py",
    title="Sources",
    icon=":material/rss_feed:",
)
scheduler = st.Page(
    "pages/scheduler.py",
    title="Scheduler",
    icon=":material/autorenew:",
)


pg = st.navigation(pages=[dashboard, sources, scheduler])

# --- RUN NAVIGATION ---
pg.run()