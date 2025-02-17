import streamlit as st
import pandas as pd
import time
from database import seasons, leagues_teams, add_team, update_favourites, get_team_by_name, get_team_matches_by_season, get_match_id_by_report_link, prepare_match_player_stats_records, upsert_players_stats, get_match_player_stats_by_team, check_and_update_data, calculate_and_display_key_team_metrics
from scrapers import scrap_match_stats

st.logo("assets/app_logo/statfield-high-resolution-logo-transparent.png", size="large") 

### DEFINITIONS

if "username" in st.session_state:
    username = st.session_state.username
if "favourites" in st.session_state:
    favourites = st.session_state.favourites

# Determine match MVP's
def calculate_mvp_score(field_players_stats_df, keepers_stats_df, selected_team, match_result):
    # Define weights for field player stats
    field_player_weights = {
        'performance_gls': 1.5,
        'performance_ast': 0.5,
        'performance_sh': 0.1,
        'performance_sot': 0.2,
        'performance_touches': 0.01,
        'performance_tkl': 0.2,
        'performance_int': 0.2,
        'performance_blocks': 0.2,
        'expected_xag': 0.5,
        'sca_sca': 0.2,
        'sca_gca': 0.5,
        'passes_cmp': 0.01,
        'passes_cmp_percent': 0.01,
        'passes_prgp': 0.05,
        'carries_carries': 0.01,
        'carries_prgc': 0.05,
        'take_ons_att': 0.02,
        'take_ons_succ': 0.05,
        'performance_crdy': -1,
        'performance_crdr': -2
    }

    keeper_weights = {
        'shot_stopping_ga': -0.5,
        'shot_stopping_saves': 0.15,
        'shot_stopping_save_percent': 0.01
    }

    mvp_scores = {}

    # Determine multipliers based on the match result
    winning_team_multiplier = 1.1  # Small boost for winning team
    loosing_team_multiplier = 0.9  # Small penalty for losing team

    # Ensure 'performance_touches' column has valid data
    if field_players_stats_df['performance_touches'].notna().sum() == 0:
        return "Insufficient data to calculate MVP for this match."
    else: 
        # Ensure required columns exist in DataFrame for field players
        for col in field_player_weights.keys():
            if col not in field_players_stats_df.columns:
                field_players_stats_df[col] = 0.0

        # Ensure required columns exist in DataFrame for keepers
        for col in keeper_weights.keys():
            if col not in keepers_stats_df.columns:
                keepers_stats_df[col] = 0.0

        # Process field players' stats
        for _, row in field_players_stats_df.iterrows():
            player = row['player_name']
            score = 0

            # Determine team-specific multiplier
            player_team = row['team']
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
                team_multiplier = 1  # No changes for draw

            # Calculate base score from standard stats
            for stat, weight in field_player_weights.items():
                stat_value = row.get(stat, 0)
                if not pd.isnull(stat_value):
                    score += stat_value * weight

            # Calculate penalty for missed penalties
            if 'performance_pkatt' in row and 'performance_pk' in row:
                if not pd.isnull(row['performance_pkatt']) and not pd.isnull(row['performance_pk']):
                    missed_penalties = row['performance_pkatt'] - row['performance_pk']
                    if missed_penalties > 0:
                        score -= missed_penalties * 2  # Penalize each missed penalty by a factor of 2

            # Calculate the difference between actual goals and xG
            if 'performance_gls' in row and 'expected_xg' in row:
                if not pd.isnull(row['performance_gls']) and not pd.isnull(row['expected_xg']):
                    goal_diff = row['performance_gls'] - row['expected_xg']
                    score += goal_diff * 1

            # Calculate success rate of take-ons (dribbles)
            if 'take_ons_att' in row and 'take_ons_succ' in row:
                if not pd.isnull(row['take_ons_att']) and row['take_ons_att'] >= 5:
                    take_on_success_rate = row['take_ons_succ'] / row['take_ons_att']
                    if take_on_success_rate > 0.4:
                        score += take_on_success_rate * 2
                    else:
                        score -= take_on_success_rate * 2

            # Apply team result multiplier
            score *= team_multiplier

            mvp_scores[player] = score

        # Process goalkeepers similarly
        for _, row in keepers_stats_df.iterrows():
            player = row['player_name']
            score = mvp_scores.get(player, 0)

            # Determine team-specific multiplier
            player_team = row['team']
            if player_team == selected_team and match_result == 'W':
                team_multiplier = winning_team_multiplier
            elif player_team == selected_team and match_result == 'L':
                team_multiplier = loosing_team_multiplier
            else:
                team_multiplier = 1  # No changes for draw

            # Calculate score for goalkeepers
            for stat, weight in keeper_weights.items():
                stat_value = row.get(stat, 0)
                if not pd.isnull(stat_value):
                    score += stat_value * weight

            # Add points for the difference between Post-Shot xG and Goals Against (GA)
            if 'shot_stopping_psxg' in row and 'shot_stopping_ga' in row:
                if not pd.isnull(row['shot_stopping_psxg']) and not pd.isnull(row['shot_stopping_ga']):
                    psxg_diff = row['shot_stopping_psxg'] - row['shot_stopping_ga']
                    if psxg_diff > 0:
                        score += psxg_diff * 1.5  # Positive effect for preventing goals
                    else:
                        score += psxg_diff * 1  # Smaller penalty for underperformance

            # Add points for the difference between Shots on Target Against (SoTA) and Goals Against (GA)
            if 'shot_stopping_sota' in row and 'shot_stopping_ga' in row:
                if not pd.isnull(row['shot_stopping_sota']) and not pd.isnull(row['shot_stopping_ga']):
                    sota_diff = row['shot_stopping_sota'] - row['shot_stopping_ga']
                    score += sota_diff * 0.5  # Award for stopping shots on target

            # Apply team result multiplier
            score *= team_multiplier

            mvp_scores[player] = score

        # Sort MVP scores in descending order
        sorted_mvp_scores = sorted(mvp_scores.items(), key=lambda x: x[1], reverse=True)

        return sorted_mvp_scores

# Prepare stats and display
def prepare_and_display_match_stats(
    team_1_field_players, team_1_keepers,
    team_2_field_players, team_2_keepers,
    selected_team, opponent, match_date, venue, sorted_mvp_scores
):
    keeper_columns = [
        "shot_stopping_sota", "shot_stopping_ga", "shot_stopping_saves", "shot_stopping_save_percent",
        "shot_stopping_psxg", "launched_att", "launched_cmp", "launched_cmp_percent", "passes_att_gk",
        "passes_thr", "passes_launch_percent", "passes_avglen","goal_kicks_att", "goal_kicks_launch_percent", 
        "goal_kicks_avglen", "crosses_opp", "crosses_stp", "crosses_stp_percent", "sweeper_opa", "sweeper_avgdist"
    ]
    general_columns = ['id', 'match_id', 'team'] 

    if not team_1_field_players.empty:
        team_1_field_players_combined = pd.concat([team_1_field_players, team_1_keepers], ignore_index=True)
        team_1_field_players_display = team_1_field_players_combined.set_index('player_name').drop(
            columns=general_columns + keeper_columns, errors='ignore'
        )
    else:
        team_1_field_players_display = pd.DataFrame()

    if not team_2_field_players.empty:
        team_2_field_players_combined = pd.concat([team_2_field_players, team_2_keepers], ignore_index=True)
        team_2_field_players_display = team_2_field_players_combined.set_index('player_name').drop(
            columns=general_columns + keeper_columns, errors='ignore'
        )
    else:
        team_2_field_players_display = pd.DataFrame()

    if not team_1_keepers.empty:
        team_1_keepers_display = team_1_keepers.set_index('player_name').filter(items=keeper_columns)
    else:
        team_1_keepers_display = pd.DataFrame()

    if not team_2_keepers.empty:
        team_2_keepers_display = team_2_keepers.set_index('player_name').filter(items=keeper_columns)
    else:
        team_2_keepers_display = pd.DataFrame()

    team_1_field_players_display = team_1_field_players_display.dropna(axis=1, how='all')
    team_1_keepers_display = team_1_keepers_display.dropna(axis=1, how='all')
    team_2_field_players_display = team_2_field_players_display.dropna(axis=1, how='all')
    team_2_keepers_display = team_2_keepers_display.dropna(axis=1, how='all')

    st.write(f"##### {selected_team} Field Players Stats")
    st.dataframe(team_1_field_players_display, use_container_width=True)

    st.write(f"##### {selected_team} Goalkeepers Stats")
    st.dataframe(team_1_keepers_display, use_container_width=True)

    st.write(f"##### {opponent} Field Players Stats")
    st.dataframe(team_2_field_players_display, use_container_width=True)

    st.write(f"##### {opponent} Goalkeepers Stats")
    st.dataframe(team_2_keepers_display, use_container_width=True)

    # Display top 3 mvps
    if isinstance(sorted_mvp_scores, list) and len(sorted_mvp_scores) >= 3:
        st.write(f"##### TOP 3 Most Valuable Players of the match for {match_date} {venue} match vs {opponent}")
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
            <div style='font-size:24px; color:#cd7f32; margin-top: 40px;'>
                🥉 {sorted_mvp_scores[2][0]}: {sorted_mvp_scores[2][1]:.2f} MVP Score
            </div>
            """, unsafe_allow_html=True)

        st.divider()
    elif sorted_mvp_scores is None:
        return
    else:
        st.error("Insufficient data to determine MVPs for this match.")
        st.divider()

# Sidebar
with st.sidebar:
    st.header('Sidebar')

    selected_team = st.session_state.get("selected_team", None)
    selected_league = st.session_state.get("selected_league", None)

    # Sidebar - League selection
    league_options = list(leagues_teams.keys())
    selected_league = st.sidebar.selectbox(
        'Select League', 
        league_options,
        index=league_options.index(selected_league) if selected_league in leagues_teams.keys() else None
    )

    # Sidebar - Team selection based on selected league
    if selected_league and selected_league != "Select League...":
        teams_list = list(leagues_teams[selected_league].keys())
        selected_team = st.sidebar.selectbox(
            'Select Team', 
            teams_list,
            index=teams_list.index(selected_team) if selected_team in teams_list else None 
        )
    else:
        selected_team = None

    # Sidebar - Season selection
    selected_season = st.sidebar.selectbox('Select Season', seasons, index=0, )

if selected_league and selected_team and selected_season and selected_team != "Select Team...":

    team_url = leagues_teams[selected_league][selected_team]
    team_url_with_season = team_url + selected_season
    team_data = get_team_by_name(selected_team)
    if team_data:
        team_id = team_data['id']
    else:
        add_team(selected_team, selected_league, team_url)
        team_data = get_team_by_name(selected_team)
        team_id = team_data['id']

    check_and_update_data(team_id=team_id, team_name=selected_team, season=selected_season, league=selected_league, update_stats=False)
    df = get_team_matches_by_season(team_id=team_id, season=selected_season)

    if df.empty:
        st.error("Failed to retrieve matchlogs. Please try again later.")
    else: 
        with st.container(border=True): team_col1, team_col2 = st.columns([3,4], gap="medium", vertical_alignment="top")
        with team_col1:
            st.subheader(f"You have selected {selected_team} from {selected_league}.")
            col1, col2 = st.columns(2)
            with col1: 
                st.image(f"assets/team_logos/{selected_league}/{selected_team}.png", width=139)
                if st.session_state.role == "fan":
                    if selected_team in favourites:
                        if st.button("Remove from Favourites"):
                            try:
                                update_favourites(username, selected_team, "remove")
                                favourites.remove(selected_team)
                                st.rerun()
                            except ValueError as e:
                                st.error(str(e))
                    else:
                        if st.button("Add to Favourites"):
                                try:
                                    update_favourites(username, selected_team, "add")
                                    favourites.append(selected_team)
                                    st.rerun()
                                except ValueError as e:
                                    st.error(str(e))
                if 'formation' in df.columns and not df['formation'].isnull().all():
                    common_formation = df['formation'].mode()[0]
                else:
                    common_formation = "No data"
                st.metric(label="Formation (most commonly used)", value=f"{common_formation}")

        with team_col2:
            calculate_and_display_key_team_metrics(df, selected_season, selected_team)
        
        st.subheader(f"Scores and fixtures of {selected_team}")
        df = df.sort_values(by='date', ascending=True)
        st.dataframe(df.drop(columns=['id', 'team_id', 'match_report_link', 'season', 'xg_filled', 'xga_filled']), use_container_width=True, hide_index=True)
    
        # Identify matches with results
        completed_matches_indices = df[~df['result'].isnull()].index.tolist()
        
        # Create buttons only for the relevant matches
        st.subheader("Player stats & MVP's")
        for idx in completed_matches_indices:
            match_date = df.at[idx, 'date']
            venue = df.at[idx, 'venue']
            opponent = df.at[idx, 'opponent']
            match_result = df.at[idx, 'result']
            match_report_link = df.at[idx, 'match_report_link']

            if match_report_link:
                if st.button(f"{match_date} {venue} match vs {opponent}", key=idx):
                    st.write(f"#### Players stats for {match_date} {venue} match vs {opponent}")
                    match_id = get_match_id_by_report_link(match_report_link)

                    if match_id:
                        (team_1_field_players, team_1_keepers), (team_2_field_players, team_2_keepers) = get_match_player_stats_by_team(
                            match_id, selected_team, opponent
                        )

                        if not team_1_field_players.empty or not team_2_field_players.empty:
                            sorted_mvp_scores = calculate_mvp_score(
                                pd.concat([team_1_field_players, team_2_field_players]),
                                pd.concat([team_1_keepers, team_2_keepers]),
                                selected_team,
                                match_result
                            )

                            prepare_and_display_match_stats(
                                team_1_field_players, team_1_keepers,
                                team_2_field_players, team_2_keepers,
                                selected_team, opponent, match_date, venue, sorted_mvp_scores
                            )
                        else:
                            field_players_stats_df, keepers_stats_df = scrap_match_stats(match_report_link, selected_team, opponent, venue)

                            if field_players_stats_df.empty or keepers_stats_df.empty:
                                st.error("No stats data available.")
                            else:
                                records = prepare_match_player_stats_records(field_players_stats_df, keepers_stats_df, match_id)
                                if records:
                                    try:
                                        upsert_players_stats(records)

                                        with st.spinner("Fetching newly added match stats..."):
                                            for _ in range(5):
                                                (team_1_field_players, team_1_keepers), (team_2_field_players, team_2_keepers) = get_match_player_stats_by_team(
                                                    match_id, selected_team, opponent
                                                )
                                                if not team_1_field_players.empty or not team_2_field_players.empty:
                                                    break
                                                time.sleep(1)

                                        if not team_1_field_players.empty or not team_2_field_players.empty:
                                            sorted_mvp_scores = calculate_mvp_score(
                                                pd.concat([team_1_field_players, team_2_field_players]),
                                                pd.concat([team_1_keepers, team_2_keepers]),
                                                selected_team,
                                                match_result
                                            )
                                            prepare_and_display_match_stats(
                                                team_1_field_players, team_1_keepers,
                                                team_2_field_players, team_2_keepers,
                                                selected_team, opponent, match_date, venue, sorted_mvp_scores
                                            )
                                        else:
                                            st.error("Unable to retrieve match stats from the database after several attempts.")
                                    except Exception as e:
                                        st.error(f"Error while upserting player stats: {e}")
                    else:
                        st.error("Match ID could not be found.")

else:
    st.title("👈 Select a team from the sidebar!")
    st.divider()
    st.info("Please select a league and team to view their match logs and stats.\nYou can also change the season selection to see past data.")
