import streamlit as st
import pandas as pd
from email_validator import validate_email, EmailNotValidError
import bcrypt
from pages.team_dashboard_page import leagues_teams
from database import (
    get_all_users,
    update_user_data,
    add_user,
    delete_user,
    get_pending_coach_requests,
    get_all_teams,
    add_team,
    update_team_data,
    delete_team,
    check_team_exists,
    update_all_matches,
    update_last_season_matches,
    update_all_match_stats,
    update_latest_match_stats
)

st.title("Admin Dashboard :material/admin_panel_settings:")

tabs = st.tabs(["Manage Users", "Coach Requests", "Manage Teams", "Database Updates"])
all_teams_df = pd.DataFrame(get_all_teams())

# Tab 1: Manage Users
with tabs[0]:
    st.subheader("Manage Users")

    users_df = get_all_users()
    users_df = users_df.sort_values(by="created_at", ascending=True)

    st.dataframe(users_df, use_container_width=True, hide_index=True)

    with st.container(border=True):
        st.write("### Edit User Details")
        username_search = st.text_input("Enter username to search for", placeholder="Username")

        selected_user = None
        if username_search:
            matching_users = users_df[users_df["username"].str.fullmatch(username_search, case=False, na=False)]

            if not matching_users.empty:
                selected_user = matching_users.iloc[0]
                st.write("User found:")
                st.dataframe(matching_users, use_container_width=True, hide_index=True)

                st.write("### Edit User Data")
                updated_username = st.text_input("Username", value=selected_user["username"])
                updated_email = st.text_input("Email", value=selected_user["email"])
                updated_password = st.text_input("Password (optional)", value="", placeholder="Leave empty to keep unchanged", type="password")
                updated_role = st.selectbox("Role", options=["fan", "coach", "admin"], index=["fan", "coach", "admin"].index(selected_user["role"]))
                updated_coach_verification = st.checkbox("Coach Verification", value=selected_user["coach_verification"])

                st.write("##### Edit Favourites")
                if updated_role == "fan":
                  st.write("Select multiple teams for fans.")
                  selected_league = st.selectbox("Select League", options=list(leagues_teams.keys()), key="fan_league")
                  
                  updated_favourites = selected_user.get("favourites", []).copy()

                  if selected_league:
                      teams_in_league = leagues_teams[selected_league]

                      selected_teams_to_add = st.multiselect(
                          "Add Teams from Selected League",
                          options=list(teams_in_league.keys()),
                          default=[],
                          key="fan_add_teams_multiselect"
                      )
                      
                      updated_favourites.extend([team for team in selected_teams_to_add if team not in updated_favourites])

                  selected_teams_to_remove = st.multiselect(
                      "Remove Teams from Favourites",
                      options=updated_favourites,
                      default=[],
                      key="fan_remove_teams_multiselect"
                  )
                  
                  updated_favourites = [team for team in updated_favourites if team not in selected_teams_to_remove]

                  st.write("###### Updated Favourite Teams: " + ", ".join(updated_favourites))

                elif updated_role == "coach":
                    st.write("Select a single team for coaches.")
                    selected_league = st.selectbox("Select League", options=list(leagues_teams.keys()), key="coach_league")

                    updated_favourites = selected_user.get("favourites", []).copy()

                    if selected_league:
                        teams_in_league = leagues_teams[selected_league]

                        updated_team = st.selectbox(
                            "Select Team",
                            options=list(teams_in_league.keys()),
                            index=0 if not updated_favourites else list(teams_in_league.keys()).index(updated_favourites[0]) if updated_favourites[0] in teams_in_league else 0,
                            key="coach_select_team"
                        )
                        
                        updated_favourites = [updated_team] 

                col1, col2 = st.columns([1, 1])

                with col1:
                    if st.button("Apply Changes"):
                        try:
                            if not updated_username.strip():
                                st.error("Username cannot be empty.")
                                st.stop()

                            try:
                                validate_email(updated_email)
                            except EmailNotValidError as e:
                                st.error(f"Invalid email: {e}")
                                st.stop()

                            current_admin_username = st.session_state.get("username")
                            if selected_user["username"] == current_admin_username:
                                if updated_role != "admin":
                                    st.error("You cannot change your own role.")
                                    st.stop()

                            if updated_role not in ["fan", "coach", "admin"]:
                                st.error("Invalid role selected.")
                                st.stop()

                            updated_data = {
                                "username": updated_username.strip(),
                                "email": updated_email.strip(),
                                "role": updated_role,
                                "favourites": updated_favourites,
                                "coach_verification": updated_coach_verification,
                            }

                            if updated_password.strip():
                                if len(updated_password.strip()) < 6:
                                    st.error("Password must be at least 6 characters long.")
                                    st.stop()
                                hashed_password = bcrypt.hashpw(updated_password.strip().encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
                                updated_data["password"] = hashed_password

                            update_user_data(selected_user["id"], updated_data)
                            st.success(f"User '{updated_username}' updated successfully.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error applying changes: {e}")

                with col2:
                    if st.button("Delete User"):
                        try:
                            current_admin_username = st.session_state.get("username")
                            delete_user(selected_user["id"], current_admin_username)
                            st.success(f"User '{selected_user['username']}' deleted successfully.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error deleting user: {e}")
            else:
                st.warning("No user found with that username.")

    with st.container(border=True):
        st.write("### Add New User")
        new_username = st.text_input("Username", key="new_username")
        new_email = st.text_input("Email", key="new_email")
        new_password = st.text_input("Password", type="password", key="new_password")
        new_role = st.selectbox("Role", options=["fan", "coach", "admin"], key="new_role")

        if new_role == "fan":
            st.write("Select multiple teams for fans.")
            new_league = st.selectbox("Select League", options=list(leagues_teams.keys()), key="new_fan_league")
            if new_league:
                teams_in_league = leagues_teams[new_league]
                new_favourites = st.multiselect("Select Favourite Teams", options=list(teams_in_league.keys()))
        elif new_role == "coach":
            st.write("Select a single team for coaches.")
            new_league = st.selectbox("Select League", options=list(leagues_teams.keys()), key="new_coach_league")
            if new_league:
                teams_in_league = leagues_teams[new_league]
                new_favourites = st.selectbox("Select Team", options=list(teams_in_league.keys()))
                new_favourites = [new_favourites]  # Ensure it's a list

        if st.button("Add User"):
            try:
                if not new_username.strip():
                    st.error("Username cannot be empty.")
                    st.stop()

                try:
                    validate_email(new_email)
                except EmailNotValidError as e:
                    st.error(f"Invalid email: {e}")
                    st.stop()

                if len(new_password.strip()) < 6:
                    st.error("Password must be at least 6 characters long.")
                    st.stop()

                hashed_password = bcrypt.hashpw(new_password.strip().encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

                add_user({
                    "username": new_username.strip(),
                    "email": new_email.strip(),
                    "password": hashed_password,
                    "role": new_role,
                    "favourites": new_favourites,
                })
                st.success(f"User '{new_username}' added successfully.")
                st.rerun()
            except Exception as e:
                st.error(f"Error adding user: {e}")

# Tab 2: Coach Requests
with tabs[1]:
    st.subheader("Coach Requests")

    coach_requests_df = get_pending_coach_requests()

    if not coach_requests_df.empty:
        st.dataframe(coach_requests_df, use_container_width=True, hide_index=True)
        
        with st.container(border=True):
          st.write("### Respond to a Coach Request")
          selected_request_id = st.selectbox(
              "Select Request ID",
              options=coach_requests_df["id"].tolist(),
              format_func=lambda x: f"Request ID: {x}",
              key="selected_coach_request"
          )

          if selected_request_id:
              selected_request = coach_requests_df[coach_requests_df["id"] == selected_request_id].iloc[0]
              st.write(f"Selected Request for User: {selected_request['username']} (Email: {selected_request['email']})")

              st.write("### Approve Request")
              assigned_team = st.selectbox("Assign a Team", all_teams_df["name"].tolist(), key="assign_team")

              if st.button("Approve Request"):
                  try:
                      if not assigned_team:
                          st.error("You must assign a team to approve the request.")
                          st.stop()

                      update_user_data(
                          selected_request["id"],
                          {"role": "coach", "coach_verification": False, "favourites": [assigned_team]}
                      )
                      st.success(f"Request approved. User '{selected_request['username']}' is now a coach for '{assigned_team}'.")
                      st.rerun()
                  except Exception as e:
                      st.error(f"Error approving request: {e}")

              st.write("### Reject Request")
              if st.button("Reject Request"):
                  try:
                      update_user_data(
                          selected_request["id"],
                          {"coach_verification": False}
                      )
                      st.success(f"Request rejected for user '{selected_request['username']}'.")
                      st.rerun()
                  except Exception as e:
                      st.error(f"Error rejecting request: {e}")
          else:
              st.info("No pending coach requests.")

# Tab 3: Manage Teams
with tabs[2]:
    st.subheader("Manage Teams")

    all_teams_df = all_teams_df.sort_values(by="name", ascending=True)

    st.dataframe(all_teams_df, use_container_width=True, hide_index=True)

    with st.container(border=True):
      st.write("### Edit Team Details")
      team_name_search = st.text_input("Enter team name to search for", placeholder="Team Name")

      selected_team = None
      if team_name_search:
          matching_teams = all_teams_df[all_teams_df["name"].str.fullmatch(team_name_search, case=False, na=False)]

          if not matching_teams.empty:
              selected_team = matching_teams.iloc[0]
              st.write("Team found:")
              st.dataframe(matching_teams, use_container_width=True, hide_index=True)

              st.write("### Edit Team Data")
              updated_name = st.text_input("Team Name", value=selected_team["name"])
              updated_league = st.text_input("League", value=selected_team["league"])
              updated_team_url = st.text_input("Team URL", value=selected_team["team_url"])

              col1, col2 = st.columns([1, 1])

              with col1:
                  if st.button("Apply Changes"):
                      try:
                          if not updated_name.strip():
                              st.error("Team name cannot be empty.")
                              st.stop()

                          if not updated_league.strip():
                              st.error("League cannot be empty.")
                              st.stop()

                          if not updated_team_url.strip():
                              st.error("Team URL cannot be empty.")
                              st.stop()

                          if updated_name.strip() != selected_team["name"] and check_team_exists(updated_name.strip()):
                            st.error(f"Team '{updated_name}' already exists.")
                            st.stop()

                          updated_data = {
                              "name": updated_name.strip(),
                              "league": updated_league.strip(),
                              "team_url": updated_team_url.strip()
                          }

                          update_team_data(selected_team["id"], updated_data)
                          st.success(f"Team '{updated_name}' updated successfully.")
                          st.rerun()
                      except Exception as e:
                          st.error(f"Error applying changes: {e}")

              with col2:
                  if st.button("Delete Team"):
                      try:
                          delete_team(selected_team["id"])
                          st.success(f"Team '{selected_team['name']}' deleted successfully.")
                          st.rerun()
                      except Exception as e:
                          st.error(f"Error deleting team: {e}")

          else:
              st.warning("No team found with that name.")
    with st.container(border=True):
      st.write("### Add New Team")
      new_team_name = st.text_input("Team Name", key="new_team_name")
      new_team_league = st.text_input("League", key="new_team_league")
      new_team_url = st.text_input("Team URL", key="new_team_url")

      if st.button("Add Team"):
          try:
              if not new_team_name.strip():
                  st.error("Team name cannot be empty.")
                  st.stop()

              if not new_team_league.strip():
                  st.error("League cannot be empty.")
                  st.stop()

              if not new_team_url.strip():
                  st.error("Team URL cannot be empty.")
                  st.stop()

              add_team(new_team_name.strip(), new_team_league.strip(), new_team_url.strip())
              st.success(f"Team '{new_team_name}' added successfully.")
              st.rerun()
          except Exception as e:
              st.error(f"Error adding team: {e}")

      st.write("### Add Teams from CSV")
      csv_file = st.file_uploader("Upload CSV File", type=["csv"], key="teams_csv")

      if csv_file:
          if st.button("Apply"):
            try:
                csv_df = pd.read_csv(csv_file)

                if not all(col in csv_df.columns for col in ["name", "league", "team_url"]):
                    st.error("CSV must contain 'name', 'league', and 'team_url' columns.")
                    st.stop()

                total_teams = len(csv_df)
                progress_text = "Adding teams to the database. Please wait..."
                my_bar = st.progress(0, text=progress_text)

                for index, row in csv_df.iterrows():
                    try:
                        add_team(row["name"].strip(), row["league"].strip(), row["team_url"].strip())
                    except Exception as e:
                        st.error(f"Error adding team '{row['name']}': {e}")
                    
                    # Update progress bar
                    progress_percentage = int(((index + 1) / total_teams) * 100)
                    my_bar.progress(progress_percentage, text=progress_text)

                my_bar.empty()
                st.rerun()
            except Exception as e:
                st.error(f"Error processing CSV file: {e}")

# Tab 4: Database Updates
with tabs[3]:
    st.subheader("Database Updates")

    col1, col2 = st.columns(2)
    with col1:
      st.write("#### Manual Update Team Matchlogs :material/update:")
      if st.button("Update all seasons matchlogs", help="It will take more than an hour!!!"):
        with st.spinner("Fetching data..."):
            update_all_matches()
        st.success("✅ Team matchlogs has been updated!")

      if st.button("Update latest season matches"): 
        with st.spinner("Fetching data..."):
            update_last_season_matches()
        st.success("✅ Team matchlogs has been updated!")
    with col2:
      st.write("#### Manual Update Team Match Statistics :material/update:")
      if st.button("Update all match stats", help="This will take a long time!!!"):
          with st.spinner("Fetching player statistics..."):
              update_all_match_stats()
          st.success("✅ Player statistics have been updated!")

      if st.button("Update latest season match stats"):
          with st.spinner("Fetching player statistics..."):
              update_latest_match_stats()
          st.success("✅ Player statistics have been updated!")