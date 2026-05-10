import streamlit as st
import plotly.express as px
from datetime import datetime, date, time, timedelta
import time as tm
import pandas as pd




def refresh():
    st.session_state.articles_count = articles_count()
    st.session_state.sentiment_count = sentiment_count()
    st.session_state.keyword_count = keyword_count()
    st.session_state.entities_count = entities_count()
    tm.sleep(3)
    st.rerun()

def get_filter():
    selected_sources = [ item['_id'] for item in sources if item['name'] in st.session_state.selected_sources ]
    if len(selected_sources) == 0:
        selected_sources = None
    
    
    date_range = st.session_state.date_range
    start_date = None
    end_date = None

    if isinstance(date_range, tuple):
        if len(date_range) > 0:
            start_date = date_range[0]
        if len(date_range) > 1:
            end_date = date_range[1]
            
    
    start_ts = int(tm.mktime(datetime.combine(start_date, time(0, 0, 0)).timetuple())) if start_date else None
    end_ts = int(tm.mktime(datetime.combine(end_date, time(23, 59, 59)).timetuple())) if end_date else None
            
    return selected_sources, start_ts, end_ts

def get_query():
    sources, start_date, end_date = get_filter()
    
    must = []

    # date filtering
    range_filter = {}
    if start_date is not None:
        range_filter["gte"] = start_date
    if end_date is not None:
        range_filter["lte"] = end_date
    

    if range_filter:
        must.append({
            "range": {
                "published": range_filter
            }
        })
        
    # source filter

    if sources:
        must.append({
            "terms": {
                "source_id.keyword": sources
            }
        })
        
    query = {
        "bool": {
                "must": must
            }
    }
    
    return query

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

def sentiment_count():
    
    query = get_query()
    
    response = st.session_state.es_client.search(
        index="news",
        size=0,   # no need to return docs
        query=query,
        aggs={
            "sentiment_count": {
                "terms": {
                    "field": "sentiment.keyword",  # use keyword for exact match
                    "size": 10
                }
            }
        }
    )

    # extract counts
    buckets = response["aggregations"]["sentiment_count"]["buckets"]
    sentiment_count = {b["key"]: b["doc_count"] for b in buckets}
    
    return sentiment_count

def entities_count():
    
    query = get_query()
     
    response = st.session_state.es_client.search(
        index="news",
        size=0,   # no docs, only aggregation
        query=query,
        aggs={
            "top_entities": {
                "terms": {
                    "field": "entities.keyword",  # exact keyword
                    "size": 15,                  # top 20 keywords
                    "order": {"_count": "desc"}  # sort by count
                }
            }
        }
    )

    # extract keywords and counts
    buckets = response["aggregations"]["top_entities"]["buckets"]
    top_entities = {b["key"]: b["doc_count"] for b in buckets}
    
    return top_entities

def keyword_count():
    
    query = get_query()
     
    response = st.session_state.es_client.search(
        index="news",
        size=0,   # no docs, only aggregation
        query=query,
        aggs={
            "top_keywords": {
                "terms": {
                    "field": "keywords.keyword",  # exact keyword
                    "size": 15,                  # top 20 keywords
                    "order": {"_count": "desc"}  # sort by count
                }
            }
        }
    )

    # extract keywords and counts
    buckets = response["aggregations"]["top_keywords"]["buckets"]
    top_keywords = {b["key"]: b["doc_count"] for b in buckets}
    
    return top_keywords

def articles_count(sources = None, start_date = None, end_date = None):
    
    
    query = get_query()
    
    
    response = st.session_state.es_client.search(
        index="news",
        size=0,
        query=query,
        aggs={
            "articles_per_source": {
                "terms": {
                    "field": "source_name.keyword",
                    "size": 10,     # return only top 10
                    "order": {
                        "_count": "asc"   # sort by count descending
                    }
                }
            }
        }
    )

    buckets = response["aggregations"]["articles_per_source"]["buckets"]

    # convert buckets to dict
    result = {b["key"]: b["doc_count"] for b in buckets}
    
    result = dict(
        sorted(result.items(), key=lambda x: x[1], reverse=True)[:10]
    )

    return result

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
st.title("Dashboard")
col1, col2, col3 = st.columns([1,1,1],vertical_alignment="bottom")
# filter
with col1:
    sources = fetch_sources()
    options = [s['name'] for s in sources]
    st.session_state.selected_sources = st.multiselect(
        "Sources:",
        options
    )


with col2:
    st.session_state.date_range = st.date_input(
        "Select date range",
        value=(date.today() - timedelta(days=5), "today")
    )
    
with col3:
    if st.button("Refresh", type="primary"):
        refresh()

# space       
st.write("")

col1, col2 = st.columns([1,1],vertical_alignment="center")
with col1:
    
    st.write("Number of articles by source")
    
    if "articles_count" not in st.session_state:
        st.session_state.articles_count = articles_count()
        
    if st.session_state.articles_count:
        st.bar_chart(st.session_state.articles_count, sort=False, color="#0e3a80")
    else:
        st.bar_chart(pd.DataFrame({"count": [0]}, index=["No data"]))
with col2:
    st.write("Top keywords")
    
    if "keyword_count" not in st.session_state:
        st.session_state.keyword_count = keyword_count()
    
    if st.session_state.keyword_count:
        st.bar_chart(st.session_state.keyword_count, sort=False , color="#c2305a")
    else:
        st.bar_chart(pd.DataFrame({"count": [0]}, index=["No data"]))

col1, col2 = st.columns([1,1],vertical_alignment="center")
with col1:
    st.write("Top entities")
    
    if "entities_count" not in st.session_state:
        st.session_state.entities_count = entities_count()
        
    if st.session_state.entities_count:
        st.bar_chart(st.session_state.entities_count, sort=False, color="#186b38")
    else:
        st.bar_chart(pd.DataFrame({"count": [0]}, index=["No data"]))
        
    
    
with col2:
    
    if "sentiment_count" not in st.session_state:
        st.session_state.sentiment_count = sentiment_count()
        
        
    sentiment_count = st.session_state.sentiment_count
    labels = list(sentiment_count.keys())
    values = list(sentiment_count.values())
    fig = px.pie(
        names=labels,
        values=values,
        color=labels,
        color_discrete_map={
            'POSITIVE': '#074a20',  # green
            'NEGATIVE': '#9c0606'   # red
        }
    )
    st.write("Article Sentiment Distribution")
    st.plotly_chart(fig, width="stretch")