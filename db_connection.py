import streamlit as st

conn = st.connection("sql", type="sql")

def get_users():
  session = conn.session()
  return session.table("users").to_pandas()