import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from database import get_team_matches_by_season, get_players_stats, get_team_by_name

team_name = st.session_state.favourites[0]
team_data = get_team_by_name(team_name)
team_id = team_data['id']
team_league = team_data['league']
seasons = ['2024-2025', '2023-2024', '2022-2023', '2021-2022', '2020-2021', 
           '2019-2020', '2018-2019', '2017-2018', '2016-2017', '2015-2016', '2014-2015']

col1, col2 = st.columns([1,11])
with col1:
  st.image(f"assets/team_logos/{team_league}/{team_name}.png", width=64)
with col2:
  st.title(f"{team_name} Coach Dashboard ⚽:material/sports:")

with st.sidebar:
  selected_season = st.selectbox("Select season:", seasons)

matches_df = get_team_matches_by_season(team_id, selected_season)
played_matches = matches_df[matches_df['result'].notna()]

tab1, tab2, tab3 = st.tabs(["Team Analysis", "Player Analysis", "Match Analysis"])

# with tab1:
#     st.header("📊 Team Analysis")
#     st.write("asdadsad")

# with tab2:
#     st.header("🔍 Player Analysis")
#     st.write("asdadad")

# with tab3:
#     st.header("📋 Match Analysis")
#     if not matches_df.empty:
#         matches_df = get_team_matches_by_season(team_id, selected_season)
#         matches_df['date'] = pd.to_datetime(matches_df['date'])
#         played_matches = matches_df[matches_df['result'].notna()]
#         future_matches = matches_df[matches_df['result'].isna()].sort_values(by='date')
#         next_match = future_matches.iloc[:1] if not future_matches.empty else pd.DataFrame()
#         filtered_matches = pd.concat([played_matches, next_match])
#         filtered_matches = filtered_matches.sort_values(by='date')
#         match_options = filtered_matches.apply(lambda row: f"{row['date'].strftime('%Y-%m-%d')} - {row['opponent']} ({row['result'] if pd.notna(row['result']) else 'Upcoming'})", axis=1).tolist()
#         selected_match = st.selectbox("Select match:", match_options)
#     else:
#         st.warning("There are no matches available for this team in the selected season.")
#         match_id = None

# Team Analysis
with tab1:
    st.header("📊 Team Analysis")
    if not played_matches.empty:
        played_matches['date'] = pd.to_datetime(played_matches['date'])
        played_matches['gf_clean'] = played_matches['gf'].apply(
            lambda x: float(x.split('(')[0]) if isinstance(x, str) else float(x) if pd.notna(x) else 0.0
        )
        played_matches['xg'] = played_matches['xg'].astype(float)

        # xG vs Gole
        fig, ax = plt.subplots()
        ax.bar(played_matches['date'], played_matches['gf_clean'], label="Goals", alpha=0.7)
        ax.plot(played_matches['date'], played_matches['xg'], marker='o', color='red', label="xG")
        ax.set_title("Expected Goals (xG) vs Goals Scored")
        ax.legend()
        st.pyplot(fig)

        # Posiadanie piłki vs Wyniki
        played_matches['points'] = played_matches['result'].apply(lambda x: 3 if "W" in x else 1 if "D" in x else 0)
        fig, ax = plt.subplots()
        ax.scatter(played_matches['possession'], played_matches['points'], alpha=0.7)
        ax.set_title("Possession vs Points Earned")
        ax.set_xlabel("Possession (%)")
        ax.set_ylabel("Points")
        st.pyplot(fig)
    else:
        st.warning("No played matches available for this season.")

# Player Analysis
with tab2:
    st.header("🔍 Player Analysis")
    if not played_matches.empty:
        match_ids = played_matches['id'].tolist()
        players_stats = pd.concat([get_players_stats(mid) for mid in match_ids])
        if not players_stats.empty:
            # Top strzelcy
            top_scorers = players_stats.groupby('player_name')['performance_gls'].sum().sort_values(ascending=False).head(5)
            fig, ax = plt.subplots()
            top_scorers.plot(kind='bar', ax=ax, color='blue')
            ax.set_title("Top Scorers")
            st.pyplot(fig)

            # Skuteczność podań
            pass_accuracy = players_stats.groupby('player_name')['passes_cmp_percent'].mean().sort_values(ascending=False).head(10)
            fig, ax = plt.subplots()
            pass_accuracy.plot(kind='bar', ax=ax, color='green')
            ax.set_title("Pass Accuracy (%)")
            st.pyplot(fig)
        else:
            st.warning("No player statistics available for this season.")
    else:
        st.warning("No played matches available for this season.")

# Match Analysis
with tab3:
    st.header("📋 Match Analysis")
    if not matches_df.empty:
        matches_df['date'] = pd.to_datetime(matches_df['date'])
        played_matches = matches_df[matches_df['result'].notna()]
        future_matches = matches_df[matches_df['result'].isna()].sort_values(by='date')
        next_match = future_matches.iloc[:1] if not future_matches.empty else pd.DataFrame()
        filtered_matches = pd.concat([played_matches, next_match])
        filtered_matches = filtered_matches.sort_values(by='date')
        match_options = filtered_matches.apply(lambda row: f"{row['date'].strftime('%Y-%m-%d')} - {row['opponent']} ({row['result'] if pd.notna(row['result']) else 'Upcoming'})", axis=1).tolist()
        selected_match = st.selectbox("Select match:", match_options)
        match_id = matches_df[matches_df.apply(lambda row: f"{row['date'].strftime('%Y-%m-%d')} - {row['opponent']} ({row['result'] if pd.notna(row['result']) else 'Upcoming'})", axis=1) == selected_match]['id'].values[0]
        match_stats = get_players_stats(match_id)

        if not match_stats.empty:
            # Strzały celne vs Strzały oddane
            fig, ax = plt.subplots()
            ax.bar(match_stats['player_name'], match_stats['performance_sh'], label="Shots", alpha=0.7)
            ax.bar(match_stats['player_name'], match_stats['performance_sot'], label="Shots on Target", alpha=0.7)
            ax.set_title("Shots vs Shots on Target")
            ax.legend()
            plt.xticks(rotation=90)
            st.pyplot(fig)
        else:
            st.warning("No player statistics available for this match.")
    else:
        st.warning("There are no matches available for this team in the selected season.")