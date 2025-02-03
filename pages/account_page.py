import streamlit as st
from database import supabase
import bcrypt
from pages.team_dashboard_page import leagues_teams
from email_validator import validate_email, EmailNotValidError

st.title("Account Settings :material/settings:")
st.header(f"Hello, {st.session_state.username}!")

col1, col2 = st.columns(2)

with col1:
  st.subheader("Change Username")
  current_username = st.text_input("Current Username", value=st.session_state.username, disabled=True)
  new_username = st.text_input("New Username")
  confirm_username = st.text_input("Confirm New Username")

  if st.button("Update Username"):
      if not new_username or not confirm_username:
          st.error("All fields are required.")
      elif new_username != confirm_username:
          st.error("New usernames do not match.")
      elif new_username == st.session_state.username:
          st.error("The new username must be different from the current one.")
      else:
          response = supabase.table("users").select("*").eq("username", new_username).execute()
          if response.data:
              st.error("The new username is already taken. Please choose a different one.")
          else:
              update_response = supabase.table("users").update({"username": new_username}).eq("username", st.session_state.username).execute()
              if update_response.data:
                  st.session_state.username = new_username  
                  st.rerun()
              else:
                  st.error("Failed to update username. Please try again.")
with col2:
  st.subheader("Change Email Address")
  response = supabase.table("users").select("email").eq("username", st.session_state.username).execute()
  if response.data:
      current_email = response.data[0]["email"]
  else:
      current_email = ""

  current_email_display = st.text_input("Current Email", value=current_email, disabled=True)
  new_email = st.text_input("New Email Address")
  confirm_email = st.text_input("Confirm New Email Address")

  if st.button("Update Email"):
      if not new_email or not confirm_email:
          st.error("All fields are required.")
      elif new_email != confirm_email:
          st.error("New email addresses do not match.")
      elif new_email == current_email:
          st.error("The new email address must be different from the current one.")
      else:
          try:
            validate_email(new_email)
            response = supabase.table("users").update({"email": new_email}).eq("username", st.session_state.username).execute()
            if response.data:
                st.success("Email updated successfully!")
                st.rerun()
            else:
                st.error("Failed to update email. Please try again.")
          except EmailNotValidError as e:
              st.error(f"Invalid email: {str(e)}")

with col1:
  st.subheader("Change Password")
  current_password = st.text_input("Current Password", type="password")
  new_password = st.text_input("New Password", type="password")
  confirm_password = st.text_input("Confirm New Password", type="password")

  if st.button("Update Password"):
      if not current_password or not new_password or not confirm_password:
          st.error("All fields are required.")
      elif new_password != confirm_password:
          st.error("New passwords do not match.")
      else:
          response = supabase.table("users").select("*").eq("username", st.session_state.username).execute()
          if not response.data:
              st.error("User not found.")
          else:
            user = response.data[0]
            stored_password = user["password"]

            if not bcrypt.checkpw(current_password.encode(), stored_password.encode()):
                st.error("Current password is incorrect.")
            else:
                hashed_new_password = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
                update_response = supabase.table("users").update({"password": hashed_new_password}).eq("username", st.session_state.username).execute()
                if update_response.data:
                    st.rerun()
                else:
                    st.error("Failed to update password. Please try again.")
if st.session_state.role == "fan":
    st.subheader("Update Favourite Teams")
    if "favourites" not in st.session_state or st.session_state.favourites is None:
        st.session_state.favourites = []
    selected_league = st.selectbox("Select League", list(leagues_teams.keys()))
    if selected_league:
        teams_in_league = leagues_teams[selected_league]
        selected_teams = st.multiselect("Select Your Favorite Teams", options=teams_in_league)

    if st.button("Add Teams to Favourites"):
        if not selected_teams:
            st.warning("Please select at least one team to add.")
        else:
            already_in_favourites = [team for team in selected_teams if team in st.session_state.favourites]
            new_teams = [team for team in selected_teams if team not in st.session_state.favourites]

            if already_in_favourites:
                st.warning(f"The following teams are already in your favourites: {', '.join(already_in_favourites)}")

            if new_teams:
                updated_favourites = st.session_state.favourites + new_teams
                update_response = (
                    supabase.table("users")
                    .update({"favourites": updated_favourites})
                    .eq("username", st.session_state.username)
                    .execute()
                )
                if update_response.data:
                    st.session_state.favourites = updated_favourites
                    st.rerun()
                else:
                    st.error("Failed to update favourites. Please try again.")

    if st.session_state.favourites:
        teams_to_remove = st.multiselect("Remove Teams from Favourites", options=st.session_state.favourites)
        if st.button("Remove Selected Teams"):
            if not teams_to_remove:
                st.warning("Please select at least one team to remove.")
            else:
                updated_favourites = [team for team in st.session_state.favourites if team not in teams_to_remove]
                update_response = (
                    supabase.table("users")
                    .update({"favourites": updated_favourites})
                    .eq("username", st.session_state.username)
                    .execute()
                )
                if update_response.data:
                    st.session_state.favourites = updated_favourites
                    st.rerun() 
                else:
                    st.error("Failed to update favourites. Please try again.")

    st.subheader("Coach Account Request")
    if st.checkbox("I confirm that I want to apply for a coach account."):
        if st.button("Submit Request"):
            update_response = (
                supabase.table("users")
                .update({"coach_verification": True})
                .eq("username", st.session_state.username)
                .execute()
            )
            if update_response.data:
                st.success("Your request to become a coach has been successfully submitted. Our team will review it and contact you soon.")
            else:
                st.error("Failed to submit your request. Please try again.")