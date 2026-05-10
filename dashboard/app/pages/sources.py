import streamlit as st
import pandas as pd
import requests


# Fetch sources from Elasticsearch
def fetch_sources():
    try:
        response = st.session_state.es_client.search(
            index="sources",
            query={"match_all": {}},
            size=1000  # Adjust size as needed
        )
        sources = [
            {**hit["_source"], "_id": hit["_id"]}
            for hit in response["hits"]["hits"]
        ]
        return sources
    except Exception as e:
        st.error(f"Failed to fetch sources: {str(e)}")
        return []

st.session_state.sources = fetch_sources()
st.session_state.selected = None

@st.dialog("Add source", width="medium")
def add_source(item):
    name = st.text_input("Name")
    url = st.text_input("Rss url")
    if st.button("Submit"):
        if not name:
            st.error("Please provide source name.")
            st.stop()
        if not url:
            st.error("Please provide source rss url")
            st.stop()
            
            
        source = {
            'name': name,
            'url': url
        }
        
        try:
            st.session_state.es_client.index(index="sources", document=source, refresh="wait_for")
            st.success("Source added successfully")
            st.session_state.sources = fetch_sources()
            st.rerun()
        except Exception as e:
            st.error(f"Failed to add source: {str(e)}")
            st.stop()
        
        

def delete_source(sources_ids):
    try:
        for source_id in sources_ids:
            st.session_state.es_client.delete(
                index="sources",
                id=source_id,
                refresh="wait_for"  # wait until this delete is visible in search
            )

        st.success("Sources deleted successfully")
        st.session_state.selected = None
        st.session_state.sources = fetch_sources()
        st.rerun()
    except Exception as e:
        st.error(f"Failed to delete source: {str(e)}")
        st.stop()
    
col1, col2 = st.columns([1,1],vertical_alignment="bottom")
with col1:
    st.image("logo.png", width=100)
with col2:
    
    st.markdown(
        """
        <div style="text-align: right; font-size: 12px; color: gray;">
            Powered by Datalixia
        </div>
        """,
        unsafe_allow_html=True
    )
st.write("")
# --- Page Header ---
col1, col2 = st.columns([7,1],vertical_alignment="center")

with col1:
    st.write("### Sources")
    

with col2:
    
    if st.button("Add source", type="primary", width='stretch'):
        add_source("New Source")


# --- Display DataFrame ---
if st.session_state.sources:
    df = pd.DataFrame(st.session_state.sources)
    
    st.session_state.selected = st.dataframe(df.drop(columns=["_id"]), on_select="rerun")

    if st.session_state.selected .selection.rows:
        if st.button("Delete source", type="secondary"):
            sources_ids = df.iloc[st.session_state.selected .selection.rows]["_id"].tolist()
            delete_source(sources_ids)
else:
    st.info("No sources found.")