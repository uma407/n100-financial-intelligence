import streamlit as st

st.set_page_config(
    page_title="Nifty 100 Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📊 Nifty 100 Financial Intelligence Dashboard")

st.sidebar.title("Navigation")

page = st.sidebar.radio(
    "Go to",
    [
        "🏠 Home",
        "🏢 Company Profile",
        "🔍 Screener",
        "👥 Peer Comparison",
        "📈 Trend Analysis",
        "🏭 Sector Analysis",
        "💰 Capital Allocation",
        "📄 Annual Reports"
    ]
)

if page == "🏠 Home":
    exec(open("pages/01_home.py", encoding="utf-8").read())

elif page == "🏢 Company Profile":
    exec(open("pages/02_profile.py", encoding="utf-8").read())

elif page == "🔍 Screener":
    exec(open("pages/03_screener.py", encoding="utf-8").read())

elif page == "👥 Peer Comparison":
    exec(open("pages/04_peers.py", encoding="utf-8").read())

elif page == "📈 Trend Analysis":
    exec(open("pages/05_trends.py", encoding="utf-8").read())

elif page == "🏭 Sector Analysis":
    exec(open("pages/06_sectors.py", encoding="utf-8").read())

elif page == "💰 Capital Allocation":
    exec(open("pages/07_capital.py", encoding="utf-8").read())

elif page == "📄 Annual Reports":
    exec(open("pages/08_reports.py", encoding="utf-8").read())