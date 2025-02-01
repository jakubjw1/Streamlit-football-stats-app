import streamlit as st

st.set_page_config(
    page_title="StatField",
    page_icon="assets/app_logo/statfield-favicon-green.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

from apscheduler.schedulers.background import BackgroundScheduler
from database import supabase, update_last_season_matches
from pages.fan.team_dashboard_page import leagues_teams
from email_validator import validate_email, EmailNotValidError
import bcrypt
import time

def scheduled_db_update():
    print("🔄 Running automatic scraping for the current season...")
    update_last_season_matches()
    print("✅ Matchlogs updated.")

# scheduler = BackgroundScheduler()
# scheduler.add_job(scheduled_db_update, 'interval', hours=1)
# scheduler.start()

st.logo("assets/app_logo/statfield-high-resolution-logo-transparent.png", size="large")

ROLES = [None, "fan", "coach", "admin"]

if "role" not in st.session_state:
  st.session_state.role = None
if "selected_team" not in st.session_state:
    st.session_state.selected_team = None
if "selected_league" not in st.session_state:
    st.session_state.selected_league = None
if "username" not in st.session_state:
    st.session_state.username = None
if "favourites" not in st.session_state:
    st.session_state.favourites = []
if "initialized" not in st.session_state:
    st.session_state.initialized = True
    st.rerun()

def login():
  st.title("Welcome to StatField!")
  st.header("Please log in or create a new account.")
  noAccount = st.checkbox("Check it if you don't have an account yet")
  if noAccount:
    st.subheader("Register a new account")

    username_input = st.text_input("New Username")
    email_input = st.text_input("Email Address")
    password_input = st.text_input("New Password", type="password")
    repeat_password = st.text_input("Repeat Password", type="password")
    coach_verification = st.checkbox("I want to apply for a coach account")

    if st.button("Register"):
        if not username_input or not email_input or not password_input or not repeat_password:
            st.error("All fields are required.")
            return

        if password_input != repeat_password:
            st.error("Passwords do not match.")
            return

        try:
            validate_email(email_input)
        except EmailNotValidError as e:
            st.error(f"Invalid email: {str(e)}")
            return

        response = supabase.table("users").select("username").eq("username", username_input).execute()
        if response.data:
            st.error("Username already exists.")
            return

        email_response = supabase.table("users").select("email").eq("email", email_input).execute()
        if email_response.data:
            st.error("Email address already exists.")
            return

        hashed_password = bcrypt.hashpw(password_input.encode(), bcrypt.gensalt()).decode()

        insert_response = supabase.table("users").insert({
            "username": username_input,
            "email": email_input,
            "password": hashed_password,
            "role": "fan",
            "coach_verification": coach_verification 
        }).execute()

        new_user_data = insert_response.data

        if new_user_data:
            new_user = new_user_data[0]
            st.session_state.role = new_user["role"]
            st.session_state.username = new_user["username"]
            st.session_state.email = new_user["email"]
            st.session_state.favourites = new_user.get("favourites", [])
            st.success("Account created successfully!")
            st.rerun()
        elif "error" in insert_response:
            st.error(f"An error occurred: {insert_response["error"]["message"]}")
        else:
            st.error("An unexpected error occurred. Please try again.")
  else:
        
    username_input = st.text_input("Username")
    password_input = st.text_input("Password", type="password")

    if st.button("Log in"):
      if not username_input or not password_input:
          st.error("Both username and password are required.")
          return

      response = supabase.table("users").select("*").eq("username", username_input).execute()
      data = response.data

      if not data:
          st.error("Invalid username or password.")
          return

      user = data[0]
      stored_password = user["password"] 
      if not bcrypt.checkpw(password_input.encode(), stored_password.encode()):
        st.error("Invalid username or password.")
        return

      st.session_state.role = user["role"]
      st.session_state.username = user["username"]
      st.session_state.favourites = user["favourites"]
      st.rerun()
  
def logout():
    for key in st.session_state.keys():
        del st.session_state[key]
    st.rerun()

role = st.session_state.role

login_page = st.Page(login, title="Log in", icon=":material/login:")
logout_page = st.Page(logout, title="Log out", icon=":material/logout:")
settings_page = st.Page("pages/account_page.py", title="Account", icon=":material/settings:")
main_page = st.Page("pages/fan/main_page.py", title="Main Page", icon=":material/home:")
team_dashboard_page = st.Page("pages/fan/team_dashboard_page.py", title="Team Dashboard", icon=":material/groups:")
coach_page = st.Page("pages/coach/coach_page.py", title="Coach Page", icon=":material/sports:")
admin_page = st.Page("pages/admin/admin_page.py", title="Admin Page", icon=":material/admin_panel_settings:")

account_pages = [settings_page, logout_page]
guest_pages = [main_page, team_dashboard_page, login_page]
fan_pages = [main_page, team_dashboard_page]
coach_pages = [coach_page]
admin_pages = [admin_page]

page_dict = {}
if st.session_state.role == "fan":
    favourites = st.session_state.get("favourites", [])
    if favourites:
        with st.sidebar:
            st.subheader("Your Favourite Teams")
            for team in favourites:
                selected_league = None
                for league, teams in leagues_teams.items():
                    if team in teams:
                        selected_league = league
                        break
                                
                if selected_league:
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        st.image(f"assets/team_logos/{selected_league}/{team}.png", width=30)
                    with col2:
                        if st.button(f"{team}", key=team):
                            st.session_state.selected_team = team
                            st.session_state.selected_league = selected_league
                            st.switch_page(team_dashboard_page)
    else:
        st.sidebar.write("No Favourite Teams")
        
    page_dict["Fan Dashboard"] = fan_pages
    pg = st.navigation({f"Logged in as: {st.session_state.username}": account_pages} | page_dict)
elif st.session_state.role == "coach":
    page_dict["Coach Dashboard"] = coach_pages
    pg = st.navigation({f"Logged in as: {st.session_state.username}": account_pages} | page_dict)
elif st.session_state.role == "admin":
    page_dict["Admin Dashboard"] = admin_pages
    pg = st.navigation({f"Logged in as: {st.session_state.username}": account_pages} | page_dict)
elif st.session_state.role == None:
   page_dict = guest_pages
   pg = st.navigation(page_dict)

pg.run()