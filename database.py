import streamlit as st
import pandas as pd
import unicodedata
import datetime
from st_supabase_connection import SupabaseConnection
from scrapers import scrap_team_matchlogs, scrap_match_stats

seasons = ['2024-2025', '2023-2024', '2022-2023', '2021-2022', '2020-2021', 
           '2019-2020', '2018-2019', '2017-2018', '2016-2017', '2015-2016', '2014-2015']

# App leagues and teams with their links
EPL_dict = {
  "Arsenal":"https://fbref.com/en/squads/18bb7c10/",
  "Aston Villa":"https://fbref.com/en/squads/8602292d/",
  "Bournemouth":"https://fbref.com/en/squads/4ba7cbea/",
  "Brentford": "https://fbref.com/en/squads/cd051869/",
  "Brighton":"https://fbref.com/en/squads/d07537b9/",
  "Chelsea": "https://fbref.com/en/squads/cff3d9bb/",
  "Crystal Palace": "https://fbref.com/en/squads/47c64c55/",
  "Everton": "https://fbref.com/en/squads/d3fd31cc/",
  "Fulham": "https://fbref.com/en/squads/fd962109/",
  "Ipswich Town": "https://fbref.com/en/squads/b74092de/",
  "Leicester City":"https://fbref.com/en/squads/a2d435b3/",
  "Liverpool":"https://fbref.com/en/squads/822bd0ba/",
  "Manchester City": "https://fbref.com/en/squads/b8fd03ef/",
  "Manchester United": "https://fbref.com/en/squads/19538871/",
  "Newcastle":"https://fbref.com/en/squads/b2b47a98/",
  "Nottingham Forest": "https://fbref.com/en/squads/e4a775cb/",
  "Southampton": "https://fbref.com/en/squads/33c895d4/",
  "Tottenham Hotspur": "https://fbref.com/en/squads/361ca564/",
  "West Ham":"https://fbref.com/en/squads/7c21e445/",
  "Wolves": "https://fbref.com/en/squads/8cec06e1/"
}

LaLiga_dict = {
  "Alaves":"https://fbref.com/en/squads/8d6fd021/",
  "Athletic Club":"https://fbref.com/en/squads/2b390eca/",
  "Atletico Madrid":"https://fbref.com/en/squads/db3b9613/",
  "Barcelona":"https://fbref.com/en/squads/206d90db/",
  "Betis":"https://fbref.com/en/squads/fc536746/",
  "Celta Vigo":"https://fbref.com/en/squads/f25da7fb/",
  "Espanyol":"https://fbref.com/en/squads/a8661628/",
  "Getafe":"https://fbref.com/en/squads/7848bd64/",
  "Girona":"https://fbref.com/en/squads/9024a00a/",
  "Las Palmas":"https://fbref.com/en/squads/0049d422/",
  "Leganes":"https://fbref.com/en/squads/7c6f2c78/",
  "Mallorca":"https://fbref.com/en/squads/2aa12281/",
  "Osasuna":"https://fbref.com/en/squads/03c57e2b/",
  "Rayo Vallecano":"https://fbref.com/en/squads/98e8af82/",
  "Real Madrid":"https://fbref.com/en/squads/53a2f082/",
  "Real Sociedad":"https://fbref.com/en/squads/e31d1cd9/",
  "Sevilla":"https://fbref.com/en/squads/ad2be733/",
  "Valencia":"https://fbref.com/en/squads/dcc91a7b/",
  "Valladolid":"https://fbref.com/en/squads/17859612/",
  "Villarreal":"https://fbref.com/en/squads/2a8183b3/",
}

SerieA_dict = {
  "Atalanta":"https://fbref.com/en/squads/922493f3/",
  "Bologna":"https://fbref.com/en/squads/1d8099f8/",
  "Cagliari":"https://fbref.com/en/squads/c4260e09/",
  "Como": "https://fbref.com/en/squads/28c9c3cd/",
  "Empoli":"https://fbref.com/en/squads/a3d88bd8/",
  "Fiorentina":"https://fbref.com/en/squads/421387cf/",
  "Genoa":"https://fbref.com/en/squads/658bf2de/",
  "Hellas Verona": "https://fbref.com/en/squads/0e72edf2/",
  "Internazionale":"https://fbref.com/en/squads/d609edc0/",
  "Juventus":"https://fbref.com/en/squads/e0652b02/",
  "Lazio":"https://fbref.com/en/squads/7213da33/",
  "Lecce": "https://fbref.com/en/squads/ffcbe334/",
  "Milan": "https://fbref.com/en/squads/dc56fe14/",
  "Monza": "https://fbref.com/en/squads/21680aa4/",
  "Napoli":"https://fbref.com/en/squads/d48ad4ff/",
  "Parma": "https://fbref.com/en/squads/eab4234c/",
  "Roma":"https://fbref.com/en/squads/cf74a709/",
  "Torino":"https://fbref.com/en/squads/105360fe/",
  "Udinese":"https://fbref.com/en/squads/04eea015/",
  "Venezia":"https://fbref.com/en/squads/af5d5982/",
}

Bundesliga_dict = {
   "Augsburg":"https://fbref.com/en/squads/0cdc4311/",
   "Bayern Munich": "https://fbref.com/en/squads/054efa67/",
   "Bochum" : "https://fbref.com/en/squads/b42c6323/",
   "Dortmund": "https://fbref.com/en/squads/add600ae/",
   "Eintracht Frankfurt": "https://fbref.com/en/squads/f0ac8ee6/",
   "Freiburg" : "https://fbref.com/en/squads/a486e511/",
   "Gladbach": "https://fbref.com/en/squads/32f3ee20/",
   "Heidenheim":"https://fbref.com/en/squads/18d9d2a7/",
   "Hoffenheim":"https://fbref.com/en/squads/033ea6b8/",
   "Holstein Kiel":"https://fbref.com/en/squads/2ac661d9/",
   "Leverkusen": "https://fbref.com/en/squads/c7a9f859/",
   "Mainz": "https://fbref.com/en/squads/a224b06a/",
   "RB Leipzig": "https://fbref.com/en/squads/acbb6a5b/",
   "St Pauli": "https://fbref.com/en/squads/54864664/",
   "Stuttgart": "https://fbref.com/en/squads/598bc722/",
   "Union Berlin": "https://fbref.com/en/squads/7a41008f/",
   "Werder Bremen": "https://fbref.com/en/squads/62add3bf/",
   "Wolfsburg": "https://fbref.com/en/squads/4eaa11d7/",
}

Ligue1_dict = {
   "Angers": "https://fbref.com/en/squads/69236f98/",
   "Auxerre": "https://fbref.com/en/squads/5ae09109/",
   "Brest":"https://fbref.com/en/squads/fb08dbb3/",
   "Le Havre":"https://fbref.com/en/squads/5c2737db/",
   "Lens":"https://fbref.com/en/squads/fd4e0f7d/",
   "Lille":"https://fbref.com/en/squads/cb188c0c/",
   "Lyon": "https://fbref.com/en/squads/d53c0b06/",
   "Marseille":"https://fbref.com/en/squads/5725cc7b/",
   "Monaco":"https://fbref.com/en/squads/fd6114db/",
   "Montpellier":"https://fbref.com/en/squads/281b0e73/",
   "Nantes": "https://fbref.com/en/squads/d7a486cd/",
   "Nice":"https://fbref.com/en/squads/132ebc33/",
   "Paris S-G":"https://fbref.com/en/squads/e2d8892c/",
   "Reims": "https://fbref.com/en/squads/7fdd64e0/",
   "Rennes": "https://fbref.com/en/squads/b3072e00/",
   "Saint Etienne": "https://fbref.com/en/squads/d298ef2c/",
   "Strasbourg": "https://fbref.com/en/squads/c0d3eab4/",
   "Toulouse": "https://fbref.com/en/squads/3f8c4b5f/",
}

leagues_teams = {
    'Premier League': EPL_dict,
    'La Liga': LaLiga_dict,
    'Bundesliga': Bundesliga_dict,
    'Serie A': SerieA_dict,
    'Ligue 1': Ligue1_dict
}

# Initialize connection with database
supabase = st.connection("supabase", type=SupabaseConnection)

# Database functions

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

def update_matchlogs(season=None, league=None, team_name=None, all_seasons=True):
    teams = get_all_teams()
    if isinstance(teams, list):
        teams = pd.DataFrame(teams)
    if teams.empty:
        st.warning("❌ No teams found in the database!")
        return

    if league:
        teams = teams[teams['league'] == league]
    if team_name:
        teams = teams[teams['name'] == team_name]

    if all_seasons:
        seasons_to_update = seasons
    else:
        seasons_to_update = [season] if season else [seasons[0]]
    
    st.info(f"🔄 Updating matchlogs for {len(teams)} team(s) across {len(seasons_to_update)} season(s)...")
    for season_val in seasons_to_update:
        for idx, team in teams.iterrows():
            team_name_local = team["name"]
            team_url = team["team_url"]
            team_id = team["id"]

            if season_val != seasons[0]: 
                team_url = f"{team_url}{season_val}"

            match_data = scrap_team_matchlogs(team_url)
            if match_data:
                for match in match_data:
                    match["team_id"] = team_id
                    match["season"] = season_val
                match_data = clean_data_for_db(match_data)
                upsert_match(match_data)
                st.success(f"✅ Updated matchlogs for {team_name_local} ({season_val})")
            else:
                st.warning(f"⚠️ No data found for {team_name_local} ({season_val})")
    st.success("🎉 All team matchlogs have been updated!")
                                       
def get_match_id_by_report_link(match_report_link):
    response = supabase.table("matches").select("id").eq("match_report_link", match_report_link).execute()
    if response.data:
        return response.data[0]["id"]
    return None

def upsert_match(data):
    response = supabase.table("matches").upsert(
        data, 
        on_conflict="team_id, opponent, venue, competition, round, season, notes"
    ).execute()
    return response

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
    
def check_and_update_data(team_id, team_name, season, league, update_stats=False):
    if "update_attempted" not in st.session_state:
        st.session_state.update_attempted = False

    df = get_team_matches_by_season(team_id, season)
    if df.empty:
        st.info("Updating matchlogs...")
        if not st.session_state.update_attempted:
            try:
                update_matchlogs(season=season, league=league, team_name=team_name, all_seasons=False)
            except Exception as e:
                st.error("Update matchlogs failed: " + str(e))
            st.session_state.update_attempted = True
            st.rerun()
        else:
            st.error("Matchlogs update did not succeed. Continuing without updated data.")

    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    past_missing = df[(df['date'].dt.date < datetime.date.today()) & (df['result'].isna())]
    if not past_missing.empty:
        if not st.session_state.update_attempted:
            try:
                update_matchlogs(season=season, league=league, team_name=team_name, all_seasons=False)
                if update_stats:
                    st.info(f"Also updating match stats for {team_name} in {season}")
                    update_match_stats(season=season, league=league, team_name=team_name, all_seasons=False)
            except Exception as e:
                st.error("Error updating past matches: " + str(e))
            st.session_state.update_attempted = True
            st.rerun()
        else:
            st.info("Some past matches still have missing results. Please try again later – updates usually occur the day after the round of a competition is completed.")

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
    df = pd.DataFrame(data)
    df = df.drop_duplicates(subset=["match_id", "team", "player_name", "shirt_number"])
    data = df.to_dict(orient="records")
    cleaned_data = clean_data_for_db(data)
    response = supabase.table("match_player_stats").upsert(
        cleaned_data,
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

        stats_df["team_norm"] = stats_df["team"].apply(normalize_str)
        team_1_norm = normalize_str(team_1)
        team_2_norm = normalize_str(team_2)
        
        team_1_stats = stats_df[stats_df["team_norm"] == team_1_norm]
        team_2_stats = stats_df[stats_df["team_norm"] == team_2_norm]

        team_1_field_players = team_1_stats[team_1_stats["position"] != "GK"]
        team_1_keepers = team_1_stats[team_1_stats["position"] == "GK"]

        team_2_field_players = team_2_stats[team_2_stats["position"] != "GK"]
        team_2_keepers = team_2_stats[team_2_stats["position"] == "GK"]

        return (team_1_field_players, team_1_keepers), (team_2_field_players, team_2_keepers)

    except Exception as e:
        return (pd.DataFrame(), pd.DataFrame()), (pd.DataFrame(), pd.DataFrame())

# Checks if the statistics are already in database    
def stats_exist(match_id):
    response = supabase.table("match_player_stats").select("id").eq("match_id", match_id).execute()
    if response.data and len(response.data) > 0:
        return True
    return False

def update_match_stats(season=None, league=None, team_name=None, all_seasons=True):
    teams = get_all_teams()
    if isinstance(teams, list):
        teams = pd.DataFrame(teams)
    if teams.empty:
        st.warning("❌ No teams found in the database!")
        return

    if league:
        teams = teams[teams['league'] == league]
    if team_name:
        teams = teams[teams['name'] == team_name]

    if all_seasons:
        seasons_to_update = seasons
    else:
        seasons_to_update = [season] if season else [seasons[0]]
    
    st.info(f"🔄 Updating match stats for {len(teams)} team(s) across {len(seasons_to_update)} season(s)...")
    for season_val in seasons_to_update:
        for idx, team in teams.iterrows():
            team_id = team["id"]
            team_name_local = team["name"]
            matches = get_team_matches_by_season(team_id, season_val)
            if matches.empty:
                st.warning(f"⚠️ No matches found for {team_name_local} in {season_val}")
                continue

            played_matches = matches[matches["result"].notna()]
            for idx2, match in played_matches.iterrows():
                match_id = match["id"]
                match_report_link = match["match_report_link"]
                opponent = match["opponent"]
                venue = match["venue"]

                if stats_exist(match_id):
                    continue
                if not match_report_link:
                    st.warning(f"⚠️ No match report link for {team_name_local} vs {opponent} ({season_val})")
                    continue

                st.write(f"📊 Updating stats for {team_name_local} vs {opponent} ({season_val})...")
                field_players_stats_df, keepers_stats_df = scrap_match_stats(match_report_link, team_name_local, opponent, venue)
                if field_players_stats_df.empty or keepers_stats_df.empty:
                    st.warning(f"⚠️ No player stats available for {team_name_local} vs {opponent} ({season_val})")
                    continue
                records = prepare_match_player_stats_records(field_players_stats_df, keepers_stats_df, match_id)
                if records:
                    upsert_players_stats(records)
                    st.success(f"✅ Stats updated for {team_name_local} vs {opponent} ({season_val})")
    st.success("🎉 All match stats have been updated!")

# -------------------------
# UTILITY FUNCTIONS
# -------------------------

# Replace NaN values with None or empty  
def clean_data_for_db(data):
    if isinstance(data, list): 
        return [
            {k: ("" if (pd.isna(v) or (isinstance(v, str) and v.strip().lower() == "nan")) and k=="notes" else
                 (None if pd.isna(v) or (isinstance(v, str) and v.strip().lower() == "nan") else v))
             for k, v in record.items()}
            for record in data
        ]
    elif isinstance(data, dict):  
        return {
            k: ("" if (pd.isna(v) or (isinstance(v, str) and v.strip().lower() == "nan")) and k=="notes" else
                (None if pd.isna(v) or (isinstance(v, str) and v.strip().lower() == "nan") else v))
            for k, v in data.items()
        }
    else:
        raise ValueError("Unsupported data format. Expected list or dict.")

# Returns team names without diacritics
def normalize_str(s):
    if not isinstance(s, str):
        return s
    normalized = unicodedata.normalize('NFKD', s)
    ascii_bytes = normalized.encode('ASCII', 'ignore')
    return ascii_bytes.decode('utf-8').lower()


# Additional function to calculate display key team metrics
def calculate_and_display_key_team_metrics(df, selected_season, selected_team):
        total_wins = df[df['result'] == 'W'].shape[0]
        total_draws = df[df['result'] == 'D'].shape[0]
        total_losses = df[df['result'] == 'L'].shape[0]
        matches_played = total_wins + total_draws + total_losses

        df_played = df.dropna(subset=['result']).sort_values(by='date').reset_index(drop=True)

        current_streak = 0
        for result in reversed(df_played['result']):
            if result in ['W', 'D']:
                current_streak += 1
            else:
                break

        longest_streak = 0
        temp_streak = 0
        for result in df_played['result']:
            if result in ['W', 'D']:
                temp_streak += 1
                longest_streak = max(longest_streak, temp_streak)
            else:
                temp_streak = 0

        gf_values = df_played['gf'].apply(
            lambda x: float(x.split('(')[0]) if isinstance(x, str) else float(x) if pd.notna(x) else 0.0
        )
        ga_values = df_played['ga'].apply(
            lambda x: float(x.split('(')[0]) if isinstance(x, str) else float(x) if pd.notna(x) else 0.0
        )

        average_goals_for = gf_values.mean()
        average_goals_against = ga_values.mean()
        total_goals_for = gf_values.sum()
        total_goals_against = ga_values.sum()
        average_possession = df_played['possession'].mean()

        df['xg_filled'] = df.apply(
        lambda row: float(row['gf'].split('(')[0]) if pd.isna(row['xg']) and isinstance(row['gf'], str)
        else float(row['gf']) if pd.isna(row['xg']) and pd.notna(row['gf'])
        else float(row['xg'].split('(')[0]) if isinstance(row['xg'], str)
        else row['xg'], axis=1
        )
        df['xga_filled'] = df.apply(
            lambda row: float(row['ga'].split('(')[0]) if pd.isna(row['xga']) and isinstance(row['ga'], str)
            else float(row['ga']) if pd.isna(row['xga']) and pd.notna(row['ga'])
            else float(row['xga'].split('(')[0]) if isinstance(row['xga'], str)
            else row['xga'], axis=1
        )

        df['xg_filled'] = pd.to_numeric(df['xg_filled'], errors='coerce')
        df['xga_filled'] = pd.to_numeric(df['xga_filled'], errors='coerce')

        average_xG = df['xg_filled'].mean(skipna=True)
        total_xG = df['xg_filled'].sum(skipna=True)
        average_xGA = df['xga_filled'].mean(skipna=True)
        total_xGA = df['xga_filled'].sum(skipna=True)


        home_matches = df[df['venue'] == 'Home']
        average_home_attendance = home_matches['attendance'].mean()


        st.subheader(f"Key {selected_team} metrics for season {selected_season}")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(label="📅 Matches played", value=f"{matches_played}")
            st.metric(label="🎯⚽ Goals For", value=f"{total_goals_for:.0f}")
            st.metric(label="🎯 Total xG", value=f"{total_xG:.1f}" if total_xG is not None else "No data")
            st.metric(label="⏳ Average Possession", value=f"{average_possession:.1f}%")
        with col2:
            st.metric(label="🏆 Wins", value=f"{total_wins}")
            st.metric(label="❌⚽ Goals Against", value=f"{total_goals_against:.0f}")
            st.metric(label="❌ Total xGA", value=f"{total_xGA:.1f}" if total_xGA is not None else "No data")
            st.metric(label="👥 Average Home Attendance", value=f"{average_home_attendance:.0f}") 
        with col3:
            st.metric(label="🤝 Draws", value=f"{total_draws}")
            st.metric(label="⚽📈 Average Goals For", value=f"{average_goals_for:.1f}")
            st.metric(label="🎯📊 Average xG", value=f"{average_xG:.1f}" if average_xG is not None else "No data")
            st.metric(label="🔥 Current Unbeaten Streak", value=f"{current_streak}")
        with col4:
            st.metric(label="❌ Losses", value=f"{total_losses}")
            st.metric(label="⚽📉 Average Goals Against", value=f"{average_goals_against:.1f}")
            st.metric(label="❌📊 Average xGA", value=f"{average_xGA:.1f}" if average_xGA is not None else "No data")
            st.metric(label="🔥 Longest Unbeaten Streak", value=f"{longest_streak}")