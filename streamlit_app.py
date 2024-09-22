import streamlit as st

main_page = st.Page("pages/main_page.py", title="Main Page", icon=":material/home:")
team_dashboard_page = st.Page("pages/team_dashboard_page.py", title="Team Dashboard", icon=":material/groups:")

pg = st.navigation([main_page, team_dashboard_page])
pg.run()