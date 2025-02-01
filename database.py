import streamlit as st
import pandas as pd
import datetime
import re
import time
import random
from st_supabase_connection import SupabaseConnection
from scrapers import scrap_team_matchlogs, scrap_match_stats

seasons = ['2024-2025', '2023-2024', '2022-2023', '2021-2022', '2020-2021', 
           '2019-2020', '2018-2019', '2017-2018', '2016-2017', '2015-2016', '2014-2015']

# Initialize connection with database
supabase = st.connection("supabase", type=SupabaseConnection)

# Database functions

def get_last_updated_time():
    response = supabase.table("matches").select("last_updated").order("last_updated", desc=True).limit(1).execute()
    if response.data:
        return datetime.datetime.strptime(response.data[0]["last_updated"], "%Y-%m-%dT%H:%M:%S.%fZ")
    return None

def update_last_updated_time():
    now = datetime.datetime.utcnow().isoformat()
    response = supabase.table("matches").update({"last_updated": now}).gt("id", 0).execute()
    return response

# -------------------------
# USERS
# -------------------------

# Admin functions
def get_all_users():
    response = supabase.table("users").select("*").execute()
    if response.data:
        return pd.DataFrame(response.data)
    return pd.DataFrame()

def update_user_role(user_id, new_role):
    response = supabase.table("users").update({"role": new_role}).eq("id", user_id).execute()
    return response

def add_user(user_data):
    response = supabase.table("users").insert(user_data).execute()
    if not response.data:
      response.raise_when_api_error()

def delete_user(user_id, current_admin_username):
    try:
        user_data = supabase.table("users").select("*").eq("id", user_id).execute()
        if not user_data.data:
            raise ValueError("User not found.")

        user_to_delete = user_data.data[0]
        if user_to_delete["username"] == current_admin_username:
            raise ValueError("You cannot delete your own admin account.")

        response = supabase.table("users").delete().eq("id", user_id).execute()
        if not response.data:
            return response.raise_when_api_error()
    except Exception as e:
        raise ValueError(f"An error occurred while deleting a user: {e}")

def get_pending_coach_requests():
    response = supabase.table("users").select("id, username, email, role, favourites, coach_verification").eq("coach_verification", True).execute()
    if response.data:
        return pd.DataFrame(response.data)
    return pd.DataFrame()

def update_user_data(user_id, updated_data):
    response = supabase.table("users").update(updated_data).eq("id", user_id).execute()
    if not response.data:
        raise Exception(f"Failed to update user ID {user_id}: {response.data}")

def approve_coach_request(user_id):
    response = supabase.table("users").update({"role": "coach", "coach_verification": False}).eq("id", user_id).execute()
    return response

# User functions
def update_favourites(username, team, action):
    # Fetch current favourites from the database
    response = supabase.table("users").select("favourites").eq("username", username).execute()
    if not response.data:
        raise ValueError(f'User "{username}" not found in the database.')

    favourites = response.data[0].get("favourites", [])

    if action == "add":
        if team not in favourites:
            favourites.append(team)
    elif action == "remove":
        if team in favourites:
            favourites.remove(team)
    else:
        raise ValueError('Invalid action. Use "add" or "remove".')

    # Update the user"s favourites in the database
    supabase.table("users").update({"favourites": favourites}).eq("username", username).execute()

# -------------------------
# TEAMS
# -------------------------

def get_all_teams():
    response = supabase.table("teams").select("id, name, league, team_url").execute()
    if response.data:
        return response.data
    return []

def update_team_data(team_id, updated_data):
    response = supabase.table("teams").update(updated_data).eq("id", team_id).execute()
    if not response.data:
        response.raise_when_api_error()

def check_team_exists(name):
    response = supabase.table("teams").select("id").eq("name", name).execute()
    if response.data:
        return True
    return False

def add_team(name, league, team_url):
    if check_team_exists(name):
        raise ValueError(f"Team '{name}' already exists.")
    response = supabase.table("teams").insert({"name": name, "league": league, "team_url": team_url}).execute()
    if not response.data:
        response.raise_when_api_error()

def delete_team(team_id):
    response = supabase.table("teams").delete().eq("id", team_id).execute()
    if not response.data:
        response.raise_when_api_error()

def get_team_by_name(name):
    response = supabase.table("teams").select("*").eq("name", name).execute()
    if response.data:
        return response.data[0]
    return None

def get_team_name_by_id(team_id):
    response = supabase.table("teams").select("name").eq("id", team_id).execute()
    if response.data:
        return response.data[0]["name"]
    return None

# -------------------------
# MATCHES
# -------------------------

def update_all_matches():
    teams = get_all_teams()
    if isinstance(teams, list):
      teams = pd.DataFrame(teams)

    if teams.empty:
        st.warning("❌ No teams found in the database!")
        return

    total_teams = len(teams)
    total_seasons = len(seasons)
    st.info(f"🔄 Fetching data for {total_teams} teams across {total_seasons} seasons...")

    for season in seasons:
        for idx, team in teams.iterrows():
            team_name = team["name"]
            team_url = team["team_url"]
            team_id = team["id"]

            team_url_with_season = f"{team_url}{season}"

            match_data = scrap_team_matchlogs(team_url_with_season)

            if match_data:
                for match in match_data:
                    match["team_id"] = team_id
                    match["season"] = season

                match_data = clean_data_for_db(match_data)

                upsert_match(match_data)
                st.success(f"✅ Updated {team_name} ({season})")
            else:
                st.warning(f"⚠️ No data found for {team_name} ({season})")

            wait_time = random.uniform(3, 4.5)
            time.sleep(wait_time)

    update_last_updated_time()
    st.success("🎉 All matches have been updated!")

def update_last_season_matches():
    teams = get_all_teams()
    if isinstance(teams, list):
        teams = pd.DataFrame(teams)

    if teams.empty:
        return "No teams found in the database!"

    for idx, team in teams.iterrows():
        team_name = team["name"]
        team_url = team["team_url"]
        team_id = team["id"]

        match_data = scrap_team_matchlogs(team_url)
        if match_data:
            for match in match_data:
                match["team_id"] = team_id
                match["season"] = seasons[0]

            match_data = clean_data_for_db(match_data)

            upsert_match(match_data)
            st.success(f"✅ Updated {team_name} ({seasons[0]})")
        else:
            st.warning(f"⚠️ No data found for {team_name} ({seasons[0]})")

        wait_time = random.uniform(3, 4.5)
        time.sleep(wait_time)

    update_last_updated_time()

# Fetch match ID by match report link                                         
def get_match_id_by_report_link(match_report_link):
    response = supabase.table("matches").select("id").eq("match_report_link", match_report_link).execute()
    if response.data:
        return response.data[0]["id"]
    return None

# Insert or update a match
def upsert_match(data):
    response = supabase.table("matches").upsert(
        data, 
        on_conflict="team_id, opponent, date, season"
    ).execute()
    return response

# Fetch matches for a given team and season
def get_team_matches_by_season(team_id, season):
    try:
        response = supabase.table("matches").select("*").match({"team_id": team_id, "season": season}).execute()
        if response.data:
            return pd.DataFrame(response.data)
        else:
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Error fetching matches: {e}")
        return pd.DataFrame() 

# -------------------------
# PLAYERS MATCH STATS
# -------------------------

# Prepare match stats records to upsert database
def prepare_match_player_stats_records(player_df, goalkeeper_df, match_id):
    gk_from_players = player_df[player_df['Pos'] == 'GK']

    gk_combined = pd.merge(
        gk_from_players,
        goalkeeper_df,
        on='Player',
        how='outer',
        suffixes=('_player', '_gk')
    )

    gk_combined['Nat'] = gk_combined['Nat_player'].combine_first(gk_combined['Nat_gk'])
    gk_combined['Age'] = gk_combined['Age_player'].combine_first(gk_combined['Age_gk'])
    gk_combined['Min'] = gk_combined['Min_player'].combine_first(gk_combined['Min_gk'])
    gk_combined['Team'] = gk_combined['Team_player'].combine_first(gk_combined['Team_gk'])

    gk_combined = gk_combined.drop(columns=['Nat_player', 'Nat_gk', 'Age_player', 'Age_gk', 'Min_player', 'Min_gk', 'Team_player', 'Team_gk'])

    player_df = player_df[player_df['Pos'] != 'GK']

    combined_df = pd.concat([player_df, gk_combined], ignore_index=True)

    records = []

    for _, row in combined_df.iterrows():
        record = {
            'match_id': match_id,
            'player_name': row.get('Player', None),
            'shirt_number': row.get('Shirt #', None),
            'nationality': row.get('Nat', None),
            'position': row.get('Pos', None),
            'age': row.get('Age', None),
            'minutes_played': row.get('Min', None),
            'performance_gls': row.get('Performance_Gls', None),
            'performance_ast': row.get('Performance_Ast', None),
            'performance_pk': row.get('Performance_PK', None),
            'performance_pkatt': row.get('Performance_PKatt', None),
            'performance_sh': row.get('Performance_Sh', None),
            'performance_sot': row.get('Performance_SoT', None),
            'performance_crdy': row.get('Performance_CrdY', None),
            'performance_crdr': row.get('Performance_CrdR', None),
            'performance_fls': row.get('Performance_Fls', None),
            'performance_fld': row.get('Performance_Fld', None),
            'performance_off': row.get('Performance_Off', None),
            'performance_crs': row.get('Performance_Crs', None),
            'performance_tklw': row.get('Performance_TklW', None),
            'performance_int': row.get('Performance_Int', None),
            'performance_og': row.get('Performance_OG', None),
            'performance_pkwon': row.get('Performance_PKwon', None),
            'performance_pkcon': row.get('Performance_PKcon', None),
            'performance_touches': row.get('Performance_Touches', None),
            'performance_tkl': row.get('Performance_Tkl', None),
            'performance_blocks': row.get('Performance_Blocks', None),
            'expected_xg': row.get('Expected_xG', None),
            'expected_npxg': row.get('Expected_npxG', None),
            'expected_xag': row.get('Expected_xAG', None),
            'sca_sca': row.get('SCA_SCA', None),
            'sca_gca': row.get('SCA_GCA', None),
            'passes_cmp': row.get('Passes_Cmp', None),
            'passes_att': row.get('Passes_Att', None),
            'passes_cmp_percent': row.get('Passes_Cmp%', None),
            'passes_prgp': row.get('Passes_PrgP', None),
            'carries_carries': row.get('Carries_Carries', None),
            'carries_prgc': row.get('Carries_PrgC', None),
            'take_ons_att': row.get('Take-Ons_Att', None),
            'take_ons_succ': row.get('Take-Ons_Succ', None),
            'shot_stopping_sota': row.get('Shot Stopping_SoTA', None),
            'shot_stopping_ga': row.get('Shot Stopping_GA', None),
            'shot_stopping_saves': row.get('Shot Stopping_Saves', None),
            'shot_stopping_save_percent': row.get('Shot Stopping_Save%', None),
            'shot_stopping_psxg': row.get('Shot Stopping_PSxG', None),
            'launched_cmp': row.get('Launched_Cmp', None),
            'launched_att': row.get('Launched_Att', None),
            'launched_cmp_percent': row.get('Launched_Cmp%', None),
            'passes_att_gk': row.get('Passes_Att (GK)', None),
            'passes_thr': row.get('Passes_Thr', None),
            'passes_launch_percent': row.get('Passes_Launch%', None),
            'passes_avglen': row.get('Passes_AvgLen', None),
            'goal_kicks_att': row.get('Goal Kicks_Att', None),
            'goal_kicks_launch_percent': row.get('Goal Kicks_Launch%', None),
            'goal_kicks_avglen': row.get('Goal Kicks_AvgLen', None),
            'crosses_opp': row.get('Crosses_Opp', None),
            'crosses_stp': row.get('Crosses_Stp', None),
            'crosses_stp_percent': row.get('Crosses_Stp%', None),
            'sweeper_opa': row.get('Sweeper_#OPA', None),
            'sweeper_avgdist': row.get('Sweeper_AvgDist', None),
            'team': row.get('Team', None),
        }

        for key, value in record.items():
            if pd.isna(value):
                record[key] = None

        records.append(record)

    return records

# Insert or update player stats
def upsert_players_stats(data):
    response = supabase.table("match_player_stats").upsert(
        data,
        on_conflict="match_id, team, player_name, shirt_number"
    ).execute()
    return response

# Fetch players stats for a given match
def get_players_stats(match_id):
    response = supabase.table("match_player_stats").select("*").eq("match_id", match_id).execute()
    if response.data:
        return pd.DataFrame(response.data)
    return pd.DataFrame()

# Fetch players stats by match id and teams
def get_match_player_stats_by_team(match_id, team_1, team_2):
    try:
        response = supabase.table("match_player_stats").select("*").eq("match_id", match_id).execute()

        if not response.data:
            return (pd.DataFrame(), pd.DataFrame()), (pd.DataFrame(), pd.DataFrame())

        stats_df = pd.DataFrame(response.data)

        team_1_stats = stats_df[stats_df["team"] == team_1]
        team_2_stats = stats_df[stats_df["team"] == team_2]

        team_1_field_players = team_1_stats[team_1_stats["position"] != "GK"]
        team_1_keepers = team_1_stats[team_1_stats["position"] == "GK"]

        team_2_field_players = team_2_stats[team_2_stats["position"] != "GK"]
        team_2_keepers = team_2_stats[team_2_stats["position"] == "GK"]

        return (team_1_field_players, team_1_keepers), (team_2_field_players, team_2_keepers)

    except Exception as e:
        return (pd.DataFrame(), pd.DataFrame()), (pd.DataFrame(), pd.DataFrame())

# Update all matchstats for all teams and all seasons
def update_all_match_stats():
    teams = get_all_teams()
    if isinstance(teams, list):
        teams = pd.DataFrame(teams)

    if teams.empty:
        st.warning("❌ No teams found in the database!")
        return

    total_teams = len(teams)
    total_seasons = len(seasons)
    st.info(f"🔄 Fetching match stats for {total_teams} teams across {total_seasons} seasons...")

    for season in seasons:
        for idx, team in teams.iterrows():
            team_id = team["id"]
            team_name = team["name"]

            matches = get_team_matches_by_season(team_id, season)
            if matches.empty:
                st.warning(f"⚠️ No matches found for {team_name} in {season}")
                continue

            played_matches = matches[matches["result"].notna()]
            for idx, match in played_matches.iterrows():
                match_id = match["id"]
                match_report_link = match["match_report_link"]
                opponent = match["opponent"]
                venue = match["venue"]

                if not match_report_link:
                    st.warning(f"⚠️ No match report link for {team_name} vs {opponent} ({season})")
                    continue

                st.write(f"📊 Updating stats for {team_name} vs {opponent} ({season})...")

                field_players_stats_df, keepers_stats_df = scrap_match_stats(match_report_link, team_name, opponent, venue)

                if field_players_stats_df.empty or keepers_stats_df.empty:
                    st.warning(f"⚠️ No player stats available for {team_name} vs {opponent} ({season})")
                    continue

                records = prepare_match_player_stats_records(field_players_stats_df, keepers_stats_df, match_id)
                if records:
                    upsert_players_stats(records)
                    st.success(f"✅ Stats updated for {team_name} vs {opponent} ({season})")

    update_last_updated_time()
    st.success("🎉 All match stats have been updated!")


def update_latest_match_stats():
    teams = get_all_teams()
    if isinstance(teams, list):
        teams = pd.DataFrame(teams)

    if teams.empty:
        st.warning("❌ No teams found in the database!")
        return

    latest_season = seasons[0] 
    matches = supabase.table("matches").select("*").eq("season", latest_season).execute()

    if matches.data:
        matches_df = pd.DataFrame(matches.data)
    else:
        st.warning(f"❌ No matches found for season {latest_season}!")
        return

    played_matches = matches_df[matches_df["result"].notna()]

    if played_matches.empty:
        st.warning(f"❌ No played matches available for season {latest_season}!")
        return

    total_matches = len(played_matches)
    st.info(f"🔄 Fetching player stats for {total_matches} played matches in {latest_season}...")

    for idx, match in played_matches.iterrows():
        match_id = match["id"]
        match_url = match["match_report_link"]
        home_team = get_team_name_by_id(match["team_id"])
        away_team = match["opponent"]
        venue = match["venue"]

        st.write(match_id, match_url, home_team, away_team, venue)
        st.write(f"📊 Updating stats for match {idx + 1}/{total_matches} ({latest_season})...")

        field_players_stats, keepers_stats = scrap_match_stats(match_url, home_team, away_team, venue)

        st.dataframe(field_players_stats)
        st.dataframe(keepers_stats)
        if field_players_stats.empty or keepers_stats.empty:
            st.warning(f"⚠️ No stats data found for match {match_id}")
            continue

        records = prepare_match_player_stats_records(field_players_stats, keepers_stats, match_id)

        if records:
            try:
                upsert_players_stats(records)
                st.success(f"✅ Updated stats for match {match_id}")
            except Exception as e:
                st.error(f"❌ Error updating stats for match {match_id}: {e}")

    st.success(f"🎉 All played match stats for {latest_season} have been updated!")



# -------------------------
# UTILITY FUNCTIONS
# -------------------------

# Replace NaN values with None
def clean_data_for_db(data):
    if isinstance(data, list): 
        return [{k: (None if pd.isna(v) else v) for k, v in record.items()} for record in data]
    elif isinstance(data, dict):  
        return {k: (None if pd.isna(v) else v) for k, v in data.items()}
    else:
        raise ValueError("Unsupported data format. Expected list or dict.")