import streamlit as st
import pandas as pd
import numpy as np

def nav_button(label):
    active = st.session_state.page == label
    
    if st.sidebar.button(label, use_container_width=True):
        st.session_state.page = label

    if active:
        st.markdown(f"""
        <style>
            div[data-testid="stSidebar"] div.stButton button[aria-label="{label}"] {{
                background-color: red !important;
                color: white !important;
                border: 2px solid #990000 !important;
            }}
        </style>
        """, unsafe_allow_html=True)
        
# ---------- Page Config ----------
st.set_page_config(
    page_title="Dashboard",
    page_icon="📊",
    layout="wide"
)

# ---------- Sidebar ----------
st.sidebar.title("Navigation")
# initialize session state
if "page" not in st.session_state:
    st.session_state.page = "Overview"

nav_button("Overview")
nav_button("Analytics")
nav_button("About")

page = st.session_state.page  # use it normally

st.sidebar.write("---")
st.sidebar.subheader("Filters")
date_range = st.sidebar.date_input("Date Range")
category = st.sidebar.selectbox("Category", ["All", "A", "B", "C"])

# Dummy example data
data = pd.DataFrame({
    "value": np.random.randint(50, 200, 20),
    "category": np.random.choice(["A", "B", "C"], 20)
})

# ---------- Overview Page ----------
if page == "Overview":
    st.title("📈 Dashboard Overview")

    # KPI Cards
    col1, col2, col3 = st.columns(3)

    col1.metric("Visitors", "12,430", "+8%")
    col2.metric("Active Users", "2,341", "+3%")
    col3.metric("Conversion", "4.8%", "-0.2%")

    st.write("---")

    # Charts
    tab1, tab2 = st.tabs(["Line Chart", "Bar Chart"])

    with tab1:
        st.subheader("Line Chart")
        st.line_chart(data["value"])

    with tab2:
        st.subheader("Bar Chart")
        st.bar_chart(data["value"])

# ---------- Analytics ----------
elif page == "Analytics":
    st.title("📊 Analytics")

    st.subheader("Raw Data")
    st.dataframe(data)

    st.write("---")
    st.subheader("Group by Category")
    st.bar_chart(data.groupby("category")["value"].sum())

# ---------- About ----------
elif page == "About":
    st.title("ℹ️ About this Dashboard")
    st.write("""
    This is a demo dashboard built using Streamlit.
    You can use it as a starting point for analytics and visualizations.
    """)

