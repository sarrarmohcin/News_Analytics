import streamlit as st
from elasticsearch import Elasticsearch
import os

# Elasticsearch connection
ELASTIC_HOST = os.environ.get("ELASTIC_HOST", "http://localhost:9200")


es = Elasticsearch(
    "http://elasticsearch:9200",
    verify_certs=False
)

st.title("Elasticsearch Document Viewer")

index_name = st.text_input("Index name", value="news")
query_text = st.text_input("Search keyword", value="")

if st.button("Search"):
    query = {
        "query": {
            "match": {
                "_all": query_text
            }
        }
    } if query_text else {"query": {"match_all": {}}}

    try:
        res = es.search(index=index_name, body=query)
        st.write(f"Found {res['hits']['total']['value']} documents:")
        for doc in res['hits']['hits']:
            st.json(doc["_source"])
    except Exception as e:
        st.error(f"Error: {e}")
