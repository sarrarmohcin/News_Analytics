import streamlit as st
import requests
import json
import pandas as pd
import time
import datetime

def get_runs():
    url = "http://prefect-server:4200/api/flow_runs/filter"
    
    payload = {
        "flows": {
            "name": {
                "any_": ["rss_scraper"]
            },
        },
        "flow_runs":{
            "state": {
                "type": {
                    "not_any_": []
                }
            }
        },
        "sort": "START_TIME_DESC",
        "limit": 25
    }
    response = requests.post(url, json=payload)

    rows = []

    for fr in response.json():

        rows.append({
            "datetime": fr.get("start_time",None),
            "duration": fr.get("total_run_time", None),
            "state": fr.get("state_type", None),
        })

    return rows
    
st.session_state.runs = get_runs()


def run():
    deployment_id =  "61086413-b127-4945-8879-a0f6c64842e4"
    url = f"http://prefect-server:4200/api/flow_runs"
    
    payload = {
        "flow_id": "03732b47-6415-4a05-a5ea-5a1df8df9376",
        "work_pool_name" : "local-pool",
        "deployment_id": deployment_id,
        "state": {
            "type": "SCHEDULED",
            "state_details": {
                "scheduled_time": datetime.datetime.utcnow().isoformat() + "Z"
            }
        }
    }
    
    response = requests.post(url, json=payload)

    if response.status_code == 201:
        print(f"Flow run initiated successfully: {response.json()}")
        time.sleep(5)
        st.session_state.runs = get_runs()
        st.rerun()
    else:
        print(f"Error initiating flow run: {response.status_code} - {response.text}")

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
    st.write("### Scheduler")

with col2:
    
    if st.button("Run now", type="primary", width='stretch'):
        run()

        
# --- Display DataFrame ---
if st.session_state.runs:
    df = pd.DataFrame(st.session_state.runs)
    
    st.dataframe(df, height=700)

else:
    st.info("No sources found.")