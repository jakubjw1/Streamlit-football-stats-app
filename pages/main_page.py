import streamlit as st

st.set_page_config(
    page_title="StatField - Main Page",
    page_icon="assets/app_logo/statfield-favicon-green.png",
    layout="centered",
    initial_sidebar_state="expanded",
)

st.logo("assets/app_logo/statfield-high-resolution-logo-transparent.png")

st.title("StatField")

st.markdown("""
This app provides easy way to follow your favourite football team performance and ton of statistics. It eases the process of exploring and analyzing football stats, and provides a lot of fun for football fans or some of useful data for professionals like coaches etc.
* **Data sources:** [fbref.com](https://fbref.com/en/)
""")

st.image("assets/gambling-football-game-bet-concept.jpg", caption="Designed by Freepik (https://www.freepik.com/)")



