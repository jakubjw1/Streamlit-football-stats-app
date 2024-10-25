import streamlit as st
import re
import pandas as pd
import requests
from bs4 import BeautifulSoup
import db_connection

### DEFINITIONS

BASE_URL = "https://fbref.com"

MAX_BUTTON_COLUMNS = 1

#### FUNCTIONS

# Team matchlogs scraper
@st.cache_data(ttl=3600)
def get_team_matchlogs(team_url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    }
    
    session = requests.Session()
    response = session.get(team_url, headers=headers)
    
    # Check for successful request
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Find the table with matchlogs
        matchlogs_table = soup.find('table', {'id': 'matchlogs_for'})
        
        df = pd.read_html(str(matchlogs_table))[0]
        
        # Extract all 'Match Report' links
        links_elements = matchlogs_table.find_all('td', {'data-stat': 'match_report'})
        match_report_links = []
        for td in links_elements:
            links = td.find_all('a', href=True)
            match_report_links.append(links[0]['href'] if links else None)

        # Create a list with the correct number of elements, initializing with None
        links_list = [None] * len(df)

        # Populate links_list with actual links
        for i, link in enumerate(match_report_links):
            if link is not None and i < len(links_list):
                links_list[i] = BASE_URL + link

        # Add Match Report Links to DataFrame
        df['Match Report Link'] = links_list

        return df
    else:
        st.error("Unable to retrieve data. HTTP Status Code: " + str(response.status_code))
        return None

# Match stats scraper
@st.cache_data(ttl=3600)    
def get_match_stats(match_url, home_team, away_team, venue):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    }
    
    session = requests.Session()
    response = session.get(match_url, headers=headers)
    
    if response.status_code == 200:
        try:
            soup = BeautifulSoup(response.text, "html.parser")
            
            field_players_stats = soup.find_all('table', id=re.compile(r'^stats_.*_summary$'))
            keepers_stats = soup.find_all('table', id=re.compile(r'^keeper_stats_.*'))

            # Check if tables exist
            if not field_players_stats:
                st.error(f"No player stats found for {home_team} vs {away_team}")
            if not keepers_stats:
                st.error(f"No keeper stats found for {home_team} vs {away_team}")

            labels, keepers_labels = [], []
            if venue == "Home":
                labels = [f"{home_team} player stats table", f"{away_team} player stats table"]
                keepers_labels = [f"{home_team} keeper stats table", f"{away_team} keeper stats table"]
            elif venue == "Away":
                labels = [f"{away_team} player stats table", f"{home_team} player stats table"]
                keepers_labels = [f"{away_team} keeper stats table", f"{home_team} keeper stats table"]

            field_players_stats_df, keepers_stats_df = [], []

            # Process field players' stats
            for i, (table, label) in enumerate(zip(field_players_stats, labels)):
                try:
                    df = pd.read_html(str(table))[0]
                    if df.empty:
                        st.warning(f"Empty table for {label}")
                        continue
                            
                    df = df.iloc[:-1, :]  # Drop summary row
                    # Flatten multi-level columns if needed
                    df.columns = ['_'.join(col).strip() if isinstance(col, tuple) else col.replace(' ', '_').strip() for col in df.columns]
                    df.rename(columns={
                        df.columns[0]: 'Player',
                        df.columns[1]: 'Shirt #',
                        df.columns[2]: 'Nat',
                        df.columns[3]: 'Pos',
                        df.columns[4]: 'Age',
                        df.columns[5]: 'Min'
                    }, inplace=True)
                    # Set 'Player' column as index
                    df.set_index('Player', inplace=True)

                    # Assign team to each player
                    df['Team'] = home_team if label.startswith(home_team) else away_team

                    st.write(f"{label}:")
                    st.dataframe(df, use_container_width=True)
                    field_players_stats_df.append(df)
                except ValueError as e:
                    st.error(f"Error reading HTML for {label}: {e}")

            # Process keepers' stats
            for i, (table, label) in enumerate(zip(keepers_stats, keepers_labels)):
                try:
                    df = pd.read_html(str(table))[0]
                    # Flatten multi-level columns if needed
                    df.columns = ['_'.join(col).strip() if isinstance(col, tuple) else col.replace(' ', '_').strip() for col in df.columns]
                    df.rename(columns={
                        df.columns[0]: 'Player',
                        df.columns[1]: 'Nat',
                        df.columns[2]: 'Age',
                        df.columns[3]: 'Min'
                    }, inplace=True)
                    # Set 'Player' column as index
                    df.set_index('Player', inplace=True)

                    # Assign team to each keeper
                    df['Team'] = home_team if label.startswith(home_team) else away_team

                    st.write(f"{label}:")
                    st.dataframe(df, use_container_width=True)
                    keepers_stats_df.append(df)
                except ValueError as e:
                    st.error(f"Error reading HTML for {label}: {e}")

            field_players_stats_df = pd.concat(field_players_stats_df) if field_players_stats_df else pd.DataFrame()
            keepers_stats_df = pd.concat(keepers_stats_df) if keepers_stats_df else pd.DataFrame()

            # Return the data for further processing
            return field_players_stats_df, keepers_stats_df
        except Exception as e:
            st.error(f"An error occurred while getting data: {e}")
            return pd.DataFrame(), pd.DataFrame()
    else:
        st.error("Unable to retrieve match report. HTTP Status Code: " + str(response.status_code))
        return pd.DataFrame(), pd.DataFrame()

# Calculate MVP
def calculate_mvp_score(field_players_stats_df, keepers_stats_df, selected_team, match_result):
    # Define weights for field player stats
    field_player_weights = {
        'Performance_Gls': 1.5,  
        'Performance_Ast': 0.5,
        'Performance_Sh': 0.1,
        'Performance_SoT': 0.2,
        'Performance_Touches': 0.01,
        'Performance_Tkl': 0.2,
        'Performance_Int': 0.2,
        'Performance_Blocks': 0.2,
        'Expected_xAG': 0.5,
        'SCA_SCA': 0.2,
        'SCA_GCA': 0.5,
        'Passes_Cmp': 0.01,
        'Passes_Cmp%': 0.01,
        'Passes_PrgP': 0.05,  
        'Carries_Carries': 0.01,  
        'Carries_PrgC': 0.05,  
        'Take-Ons_Att': 0.02,
        'Take-Ons_Succ': 0.05,  
        'Performance_CrdY': -1,  
        'Performance_CrdR': -2   
    }

    keeper_weights = {
        'Shot Stopping_GA': -0.5,
        'Shot Stopping_Saves': 0.15,
        'Shot Stopping_Save%': 0.01
    }

    mvp_scores = {} 

    # Determine multipliers based on the match result
    winning_team_multiplier = 1.1  # Small boost for winning team
    loosing_team_multiplier = 0.9  # Small penalty for losing team


    # Check if all required columns are present
    missing_field_player_stats = [stat for stat in field_player_weights if stat not in field_players_stats_df.columns]
    missing_keeper_stats = [stat for stat in keeper_weights if stat not in keepers_stats_df.columns]

    if missing_field_player_stats or missing_keeper_stats:
        st.error("Insufficient data to calculate match MVP.")
        return None

    # Process field players' stats
    for idx, row in field_players_stats_df.iterrows():
        player = idx
        score = 0

        # Determine team-specific multiplier
        player_team = row['Team']
        if match_result == 'W':
            if player_team == selected_team:
                team_multiplier = winning_team_multiplier
            else:
                team_multiplier = loosing_team_multiplier          
        elif match_result == 'L':
            if player_team == selected_team:
                team_multiplier = loosing_team_multiplier
            else:
                team_multiplier = winning_team_multiplier
        else:
            team_multiplier = 1 # No changes for draw

        # Calculate base score from standard stats
        for stat, weight in field_player_weights.items():
            if stat in field_players_stats_df.columns:
                stat_value = row.get(stat, 0)
                if not pd.isnull(stat_value):
                    score += stat_value * weight

        # Calculate penalty for missed penalties
        if 'Performance_PKatt' in row and 'Performance_PK' in row:
            if not pd.isnull(row['Performance_PKatt']) and not pd.isnull(row['Performance_PK']):
                missed_penalties = row['Performance_PKatt'] - row['Performance_PK']
                if missed_penalties > 0:
                    score -= missed_penalties * 2  # Penalize each missed penalty by a factor of 2

        # Calculate the difference between actual goals and xG
        if 'Performance_Gls' in row and 'Expected_xG' in row:
            if not pd.isnull(row['Performance_Gls']) and not pd.isnull(row['Expected_xG']):
                goal_diff = row['Performance_Gls'] - row['Expected_xG']
                score += goal_diff * 1

        # Calculate success rate of take-ons (dribbles)
        if 'Take-Ons_Att' in row and 'Take-Ons_Succ' in row:
            if not pd.isnull(row['Take-Ons_Att']) and row['Take-Ons_Att'] >= 5:
                take_on_success_rate = row['Take-Ons_Succ'] / row['Take-Ons_Att']
                if take_on_success_rate > 0.4:
                    score += take_on_success_rate * 2
                else:
                    score -= take_on_success_rate * 2

        # Apply team result multiplier
        score *= team_multiplier

        mvp_scores[player] = score

    # Process goalkeepers similarly
    for idx, row in keepers_stats_df.iterrows():
        player = idx
        score = mvp_scores.get(player, 0)

        # Determine team-specific multiplier
        player_team = row['Team']
        if player_team == selected_team and match_result == 'W':
            team_multiplier = winning_team_multiplier
        elif player_team == selected_team and match_result == 'L':
            team_multiplier = loosing_team_multiplier
        else:
            team_multiplier = 1 # No changes for draw

        # Calculate score for goalkeepers
        for stat, weight in keeper_weights.items():
            if stat in keepers_stats_df.columns:
                stat_value = row.get(stat, 0)  # Use default value if stat is missing
                if not pd.isnull(stat_value):
                    score += stat_value * weight

        # Add points for the difference between Post-Shot xG and Goals Against (GA)
        if 'Shot Stopping_PSxG' in row and 'Shot Stopping_GA' in row:
            if not pd.isnull(row['Shot Stopping_PSxG']) and not pd.isnull(row['Shot Stopping_GA']):
                psxg_diff = row['Shot Stopping_PSxG'] - row['Shot Stopping_GA']
                if psxg_diff > 0:
                    score += psxg_diff * 1.5  # Positive effect for preventing goals
                else:
                    score += psxg_diff * 1  # Smaller penalty for underperformance

        # Add points for the difference between Shots on Target Against (SoTA) and Goals Against (GA)
        if 'Shot Stopping_SoTA' in row and 'Shot Stopping_GA' in row:
            if not pd.isnull(row['Shot Stopping_SoTA']) and not pd.isnull(row['Shot Stopping_GA']):
                sota_diff = row['Shot Stopping_SoTA'] - row['Shot Stopping_GA']
                score += sota_diff * 0.5  # Award for stopping shots on target

        # Apply team result multiplier
        score *= team_multiplier

        mvp_scores[player] = score

    # Sort MVP scores in descending order
    sorted_mvp_scores = sorted(mvp_scores.items(), key=lambda x: x[1], reverse=True)

    return sorted_mvp_scores

#### DICTIONARIES 

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

seasons = ['2024-2025', '2023-2024', '2022-2023', '2021-2022', '2020-2021', 
           '2019-2020', '2018-2019', '2017-2018', '2016-2017', '2015-2016', '2014-2015']


st.set_page_config(
  page_title="StatField - Team Dashboard",
  page_icon="assets/app_logo/statfield-favicon-green.png",
  layout="wide",
  initial_sidebar_state="expanded",
)
st.logo("assets/app_logo/statfield-high-resolution-logo-transparent.png", size="large")
st.sidebar.header('Sidebar')

# Sidebar - League selection
selected_league = st.sidebar.selectbox('Select League', list(leagues_teams.keys()), index=None)

# Sidebar - Team selection based on selected league
if selected_league:
   selected_team = st.sidebar.selectbox('Select Team', leagues_teams[selected_league].keys(), index=None)

# Sidebar - Season selection
selected_season = st.sidebar.selectbox('Select Season', seasons, index=0)

if selected_league and selected_team and selected_season:

    team_url = leagues_teams[selected_league][selected_team]
    team_url_with_season = team_url + selected_season
  
    df = get_team_matchlogs(team_url_with_season)
    if df is not None:

        if 'Formation' in df.columns and not df['Formation'].isnull().all():
            common_formation = df['Formation'].mode()[0]
        else:
            common_formation = "No data"

        total_wins = df[df['Result'] == 'W'].shape[0]
        total_draws = df[df['Result'] == 'D'].shape[0]
        total_losses = df[df['Result'] == 'L'].shape[0]
        matches_played = total_wins + total_draws + total_losses

        df_played = df.dropna(subset=['Result'])
        df_reversed = df_played[::-1]

        last_loss_index = df_reversed[df_reversed['Result'] == 'L'].index

        if last_loss_index.empty:
            current_streak = len(df_reversed)
        else:
            current_streak = last_loss_index[0]
            current_streak = len(df_reversed) - last_loss_index[0] - 1

        longest_streak = 0
        temp_streak = 0

        for result in df_played['Result']:
            if result in ['W', 'D']:
                temp_streak += 1
            else:
                longest_streak = max(longest_streak, temp_streak)
                temp_streak = 0

        longest_streak = max(longest_streak, temp_streak)

        gf_is_string = df['GF'].apply(lambda x: isinstance(x, str))
        if gf_is_string.any():
            gf_values = df['GF'].apply(lambda x: float(x.split('(')[0]) if isinstance(x, str) else float(x))
        else:
            gf_values = df['GF'].astype(float)
        ga_is_string = df['GA'].apply(lambda x: isinstance(x, str))
        if ga_is_string.any():
            ga_values = df['GA'].apply(lambda x: float(x.split('(')[0]) if isinstance(x, str) else float(x))
        else:
            ga_values = df['GA'].astype(float)

        average_goals_for = gf_values.mean()
        average_goals_against = ga_values.mean()
        total_goals_for = gf_values.sum()
        total_goals_against = ga_values.sum()
        average_possession = df['Poss'].mean()

        if 'xG' in df.columns and 'xGA' in df.columns:
            average_xG = df['xG'].mean()
            total_xG = df['xG'].sum()
            average_xGA = df['xGA'].mean()
            total_xGA = df['xGA'].sum()
        else:
            average_xG = total_xG = average_xGA = total_xGA = None

        home_matches = df[df['Venue'] == 'Home']
        average_home_attendance = home_matches['Attendance'].mean()

        with st.container(border=True): team_col1, team_col2 = st.columns([3,4], gap="medium", vertical_alignment="top")
        with team_col1:
            st.subheader(f"You have selected {selected_team} from {selected_league}.")
            col1, col2 = st.columns(2)
            with col1: 
                st.image(f"assets/team_logos/{selected_league}/{selected_team}.png", width=139)
                st.metric(label="Formation (most commonly used)", value=f"{common_formation}")

        with team_col2:
            st.subheader(f"Basic {selected_team} stats for season {selected_season}")

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
                st.metric(label="🔥 Current Streak", value=f"{current_streak}")
            with col4:
                st.metric(label="❌ Losses", value=f"{total_losses}")
                st.metric(label="⚽📉 Average Goals Against", value=f"{average_goals_against:.1f}")
                st.metric(label="❌📊 Average xGA", value=f"{average_xGA:.1f}" if average_xGA is not None else "No data")
                st.metric(label="🔥 Longest Streak", value=f"{longest_streak}")

        st.subheader(f"Scores and fixtures of {selected_team}")
        st.dataframe(df.drop(columns=['Match Report', 'Match Report Link']), use_container_width=True, hide_index=True)
    
        # Identify matches with results
        completed_matches_indices = df[~df['Result'].isnull()].index.tolist()
        
        # Create buttons only for the relevant matches
        st.subheader("Player stats & MVP's")

        # Split buttons between rows and columns
        rows = [completed_matches_indices[i:i + MAX_BUTTON_COLUMNS] for i in range(0, len(completed_matches_indices), MAX_BUTTON_COLUMNS)]
        for row in rows:
            columns = st.columns(len(row))  # Create columns for the current row
            for idx, col in zip(row, columns):
                match_date = df.at[idx, 'Date']
                venue = df.at[idx, 'Venue']
                opponent = df.at[idx, 'Opponent']
                match_result = df.at[idx, 'Result']
                match_report_link = df.at[idx, 'Match Report Link']
                
                if match_report_link:  # Only create button if there's a report link
                    if col.button(f"{match_date} {venue} match vs {opponent}", key=idx):
                        st.write(f"##### Players stats for {match_date} {venue} match vs {opponent}")
                        field_players_stats_df, keepers_stats_df = get_match_stats(match_report_link, selected_team, opponent, venue)

                        if field_players_stats_df.empty or keepers_stats_df.empty:
                            st.write("No stats data available.")
                        else:
                            # Calculate and display MVP scores
                            sorted_mvp_scores = calculate_mvp_score(field_players_stats_df, keepers_stats_df, selected_team, match_result)
                            if sorted_mvp_scores and len(sorted_mvp_scores) >= 3:
                                st.write(f"##### TOP3 Most Valuable Players of the match for {match_date} {venue} match vs {opponent}")
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.markdown(f"""
                                    <div style='font-size:24px; color:silver; margin-top: 40px;'>
                                        🥈 {sorted_mvp_scores[1][0]}: {sorted_mvp_scores[1][1]:.2f} MVP Score
                                    </div>
                                    """, unsafe_allow_html=True)

                                with col2:
                                    st.markdown(f"""
                                    <div style='font-size:24px; color:gold; margin-top: 10px;'>
                                        👑 {sorted_mvp_scores[0][0]}: {sorted_mvp_scores[0][1]:.2f} MVP Score
                                    </div>
                                    """, unsafe_allow_html=True)

                                with col3:
                                    st.markdown(f"""
                                    <div style='font-size:24px; color:#cd7f32; margin-top: 50px;'>
                                        🥉 {sorted_mvp_scores[2][0]}: {sorted_mvp_scores[2][1]:.2f} MVP Score
                                    </div>
                                    """, unsafe_allow_html=True)
                            st.divider()

else:
    st.title("👈 Select a team from the sidebar!")
    st.divider()
    st.info("Please select a league and team to view their match logs and stats.\nYou can also change the season selection to see past data.")
    df = db_connection.get_users
    st.dataframe(df)
