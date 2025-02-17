import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from database import seasons, get_team_by_name, update_match_stats, stats_exist, get_players_stats, check_and_update_data, get_team_matches_by_season, calculate_and_display_key_team_metrics

metrics_per_position = {
    "GK": ["shot_stopping_sota", "shot_stopping_ga", "shot_stopping_saves", "shot_stopping_save_percent", "shot_stopping_psxg"],
    "LB": ["performance_ast", "expected_xag", "passes_cmp", "passes_att", "passes_cmp_percent", "passes_prgp", "sca_sca", "sca_gca", "performance_tkl", "performance_int"],
    "CB": ["performance_int", "performance_tkl", "performance_blocks", "passes_cmp", "passes_att", "passes_cmp_percent"],
    "RB": ["performance_ast", "expected_xag", "passes_cmp", "passes_att", "passes_cmp_percent", "passes_prgp", "sca_sca", "sca_gca", "performance_tkl", "performance_int"],
    "CM": ["performance_gls", "performance_ast", "expected_xg", "expected_xag", "passes_cmp", "passes_att", "passes_cmp_percent", "passes_prgp", "sca_sca", "sca_gca"],
    "LW": ["performance_gls", "performance_ast", "expected_xg", "expected_xag", "carries_carries", "carries_prgc", "take_ons_att", "take_ons_succ", "sca_sca", "sca_gca"],
    "RW": ["performance_gls", "performance_ast", "expected_xg", "expected_xag", "carries_carries", "carries_prgc", "take_ons_att", "take_ons_succ", "sca_sca", "sca_gca"],
    "FW": ["performance_gls", "performance_ast", "expected_xg", "expected_xag", "performance_sh", "performance_sot", "sca_sca", "sca_gca"]
}

formations = {
    "433": ["GK", "LB", "CB", "CB", "RB", "CM", "CM", "CM", "LW", "RW", "FW"],
    "4231": ["GK", "LB", "CB", "CB", "RB", "DM", "DM", "LM", "AM", "RM", "FW"],
    "442": ["GK", "LB", "CB", "CB", "RB", "LM", "CM", "CM", "RM", "FW", "FW"],
    "352": ["GK", "CB", "CB", "CB", "LWB", "CM", "CM", "CM", "RWB", "FW", "FW"],
    "343": ["GK", "CB", "CB", "CB", "LWB", "CM", "CM", "RWB", "LW", "RW", "FW"],
    "532": ["GK", "LB", "CB", "CB", "CB", "RB", "CM", "CM", "CM", "FW", "FW"],
    "541": ["GK", "LB", "CB", "CB", "CB", "RB", "LM", "CM", "CM", "RM", "FW"],
    "4312": ["GK", "LB", "CB", "CB", "RB", "CM", "CM", "CM", "AM", "FW", "FW"],
    "4123": ["GK", "LB", "CB", "CB", "RB", "DM", "CM", "CM", "LW", "RW", "FW"],
    "4141": ["GK", "LB", "CB", "CB", "RB", "DM", "LM", "CM", "CM", "RM", "FW"],
    "4222": ["GK", "LB", "CB", "CB", "RB", "DM", "DM", "RAM", "LAM", "FW", "FW"],
    "5212": ["GK", "CB", "CB", "CB", "LWB", "RWB", "CM", "CM", "CM", "FW", "FW"],
    "3412": ["GK", "CB", "CB", "CB", "LWB", "RWB", "CM", "CM", "AM", "FW", "FW"],
    "361": ["GK", "CB", "CB", "CB", "LWB", "RWB", "CM", "CM", "CM", "CM", "FW"]
}

alternate_positions = {
    "GK": ["GK"],
    "CB": ["CB"],
    "LB": ["LB", "LWB"],
    "RB": ["RB", "RWB"],
    "LWB": ["LWB", "LB", "WB"],
    "RWB": ["RWB", "RB", "WB"],
    "WB": ["WB", "LB", "RB", "LWB", "RWB"],
    "MF": ["MF", "CM", "DM", "AM"],
    "CM": ["CM", "DM", "AM"],
    "DM": ["DM", "CM"],
    "AM": ["AM", "CF", "CM"],
    "RM": ["RM", "RW"],
    "LM": ["LM", "LW"],
    "LW": ["LW", "LM"],
    "RW": ["RW", "RM"],
    "FW": ["FW", "CF", "ST", "SS"],
    "CF": ["CF", "FW", "ST", "SS"],
    "ST": ["ST", "FW", "CF", "SS"],
    "SS": ["SS", "FW", "CF", "ST"]
}
def compute_player_per90_stats(players_stats_df, selected_players, cols):
    data = {}
    numeric_cols = [col for col in cols if col != "position"]
    
    for player in selected_players:
        player_df = players_stats_df[players_stats_df['player_name'] == player].copy()
        if player_df.empty:
            continue
        for col in numeric_cols:
            player_df[col] = pd.to_numeric(player_df[col], errors='coerce')
        total_minutes = player_df["minutes_played"].sum()
        if total_minutes == 0:
            continue
        stats = {}
        for col in numeric_cols:
            if col == "minutes_played":
                stats[col] = total_minutes
            elif "percent" in col:
                weighted_avg = (player_df[col] * player_df["minutes_played"]).sum() / total_minutes
                stats[col] = weighted_avg
            else:
                stats[col] = (player_df[col].sum() / total_minutes) * 90
        stats["position"] = player_df["position"].iloc[0]
        data[player] = stats
    return pd.DataFrame(data).T

def qualifies(player_pos, required_pos):
    """
    Rozbija ciąg z pozycjami (np. "LWB, CM") i zwraca True, jeśli którakolwiek z nich
    jest równa wymaganej pozycji lub należy do alternatywnych dla niej.
    """
    # Załóżmy, że mamy już słownik alternate_positions (patrz niżej)
    positions = [p.strip().upper() for p in player_pos.split(',')]
    allowed = [required_pos.upper()] + alternate_positions.get(required_pos.upper(), [])
    return any(pos in allowed for pos in positions)

def get_recent_matches(team_id, n=3, season=None):
    """
    Pobiera ostatnie n rozegranych meczów dla danej drużyny (filtrując mecze z wynikiem).
    Jeśli podany jest sezon, używa go; w przeciwnym razie można przyjąć domyślny sezon (np. seasons[0]).
    """
    # Jeśli sezon został podany, pobieramy mecze dla tego sezonu
    if season:
        df = get_team_matches_by_season(team_id, season)
    else:
        # Jeśli nie, przyjmujemy domyślny sezon (np. pierwszy z listy seasons)
        df = get_team_matches_by_season(team_id, seasons[0])
    
    # Konwersja kolumny 'date' na datetime (przy ewentualnych błędach – NaT)
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    
    # Filtrujemy tylko mecze z wynikiem (czyli rozegrane)
    completed = df[df['result'].notna()]
    if completed.empty:
        return pd.DataFrame()
    
    # Sortujemy mecze malejąco według daty i wybieramy n ostatnich
    recent = completed.sort_values('date', ascending=False).head(n)
    return recent

def compute_recent_player_stats(team_id, recent_matches):
    """
    Dla podanych ostatnich meczów (recent_matches) pobiera statystyki zawodników,
    filtruje tylko statystyki dla naszej drużyny (przyjmując globalną zmienną team_name),
    agreguje je – sumując kolumny numeryczne – oraz zachowuje kolumnę 'position'
    (wybierając pierwszy występujący rekord), a następnie oblicza statystyki per 90 minut.
    
    Zwraca DataFrame, którego indeks to nazwy zawodników, a kolumny to statystyki "per 90".
    """
    dfs = []
    for mid in recent_matches['id']:
        df_stats = get_players_stats(mid)
        if not df_stats.empty:
            dfs.append(df_stats)
    if not dfs:
        return pd.DataFrame()
    
    # Łączymy wszystkie statystyki
    all_stats = pd.concat(dfs, ignore_index=True)
    # Filtrujemy tylko dane dotyczące naszej drużyny (globalna zmienna team_name)
    team_stats = all_stats[all_stats['team'] == team_name].copy()
    if team_stats.empty:
        return pd.DataFrame()
    
    # Wybieramy kolumny numeryczne
    numeric_cols = team_stats.select_dtypes(include=[np.number]).columns.tolist()
    # Grupujemy statystyki według zawodnika – dla kolumn numerycznych sumujemy wartości
    aggregated_numeric = team_stats.groupby("player_name")[numeric_cols].sum()
    # Dla kolumny 'position' wybieramy pierwszy napotkany wpis (możesz też użyć np. mode)
    aggregated_positions = team_stats.groupby("player_name")["position"].apply(
        lambda x: ", ".join(sorted(x.dropna().unique())))
    
    # Łączymy wyniki w jeden DataFrame
    aggregated = aggregated_numeric.copy()
    aggregated["position"] = aggregated_positions
    
    # Obliczamy statystyki per 90 minut (dla kolumn numerycznych oprócz 'minutes_played')
    per90 = aggregated.copy()
    for col in numeric_cols:
        if col != "minutes_played":
            per90[col] = (aggregated[col] / aggregated["minutes_played"]) * 90
    return per90

def compute_composite_score(season_stats, recent_stats, metrics, weight=0.7):
    """
    Oblicza composite score jako wagowaną sumę średniej wartości metryk z sezonu (per90)
    oraz średniej wartości metryk z ostatnich meczów.
    
    Parameters:
      season_stats: Series z sezonowymi statystykami per90 (dla danego zawodnika)
      recent_stats: Series z statystykami per90 z ostatnich meczów (recent form)
      metrics: lista metryk (np. ["performance_gls", "performance_ast", ...])
      weight: waga dla statystyk sezonowych (domyślnie 0.7); (1-weight) – dla recent form.
    
    Zwraca:
      composite score – liczba.
    """
    # Jeśli recent_stats nie są dostępne, używamy statystyk sezonowych
    if recent_stats is None:
        recent_stats = season_stats
    # Dla uproszczenia: composite = weight * mean(season) + (1-weight) * mean(recent)
    season_val = np.mean([season_stats.get(m, 0) for m in metrics])
    recent_val = np.mean([recent_stats.get(m, 0) for m in metrics])
    return weight * season_val + (1 - weight) * recent_val

def propose_starting_eleven(team_stats, formation, metrics_per_position):
    """
    Dobiera wyjściową jedenastkę na podstawie statystyk (per 90) zawodników z recent_matches.
    
    team_stats: DataFrame z sezonowymi statystykami per 90 (indeks = nazwy zawodników).
    formation: Lista wymaganych pozycji, np. ["GK", "LB", "CB", "CB", "RB", "CM", "CM", "CM", "LW", "RW", "FW"].
    metrics_per_position: Słownik przypisujący dla każdej pozycji listę metryk.
    min_minutes: Minimalna liczba minut rozegranych, by zawodnik był brany pod uwagę.
    weight: Waga statystyk sezonowych w composite score (reszta – recent form); tutaj uproszczamy, używamy tylko statystyk z team_stats.
    
    Zwraca:
      Słownik: {wymagana_pozycja: zawodnik}
    """
    eligible = team_stats.copy()
    lineup = []
    remaining = eligible.copy()
    formation_with_keys = []
    counts = {}
    for pos in formation:
        counts[pos] = counts.get(pos, 0) + 1
        formation_with_keys.append(f"{pos}_{counts[pos]}")
    
    for formation_key in formation_with_keys:
        req_pos = formation_key.split("_")[0]
        # Wybieramy kandydatów, którzy kwalifikują się do wymaganej pozycji
        candidates = remaining[remaining["position"].apply(lambda pos: qualifies(pos, req_pos))]
        if candidates.empty:
            lineup.append((formation_key, None))
            continue
        metrics = metrics_per_position.get(req_pos, [])
        scores = {}
        for player in candidates.index:
            player_stats = candidates.loc[player]
            values = []
            for m in metrics:
                try:
                    values.append(float(player_stats[m]))
                except (KeyError, TypeError, ValueError):
                    values.append(0)
            if values:
                scores[player] = np.mean(values)
            else:
                scores[player] = 0
        best_player = max(scores, key=scores.get)
        lineup.append((formation_key, best_player))
        remaining = remaining.drop(best_player)
    return lineup

team_name = st.session_state.favourites[0]
team_data = get_team_by_name(team_name)
team_id = team_data['id']
team_league = team_data['league']

col1, col2 = st.columns([1, 11])
with col1:
    st.image(f"assets/team_logos/{team_league}/{team_name}.png", width=64)
with col2:
    st.title(f"{team_name} Coach Dashboard ⚽ :material/sports:")

with st.sidebar:
    selected_season = st.selectbox("Select season:", seasons, index=0)

check_and_update_data(team_id=team_id, team_name=team_name, season=selected_season, league=team_league, update_stats=True)
df = get_team_matches_by_season(team_id=team_id, season=selected_season)

if not df.empty:
    df['date'] = pd.to_datetime(df['date'])
    df.loc[:, 'gf_clean'] = df['gf'].apply(
        lambda x: float(x.split('(')[0]) if isinstance(x, str) and '(' in x else float(x) if pd.notna(x) else 0.0
    )
    df.loc[:, 'ga_clean'] = df['ga'].apply(
        lambda x: float(x.split('(')[0]) if isinstance(x, str) and '(' in x else float(x) if pd.notna(x) else 0.0
    )
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

def safe_stats_exist(match_id):
    try:
        return stats_exist(match_id)
    except Exception as e:
        return True

played_matches = df[df['result'].notna()].copy()
missing_stats = any(not safe_stats_exist(row['id']) for idx, row in played_matches.iterrows())
if missing_stats:
    st.info("Some match stats are missing. Updating match stats for the selected team and season...")
    update_match_stats(season=selected_season, league=team_league, team_name=team_name, all_seasons=False)
    st.rerun()

#############################################
# AGREGOWANE STATYSTYKI Z ZAWODNIKÓW
#############################################
if not played_matches.empty:
    match_ids = played_matches['id'].tolist()
    dfs = []
    for mid in match_ids:
        df_mid = get_players_stats(mid)
        if not df_mid.empty:
            df_mid = df_mid.dropna(axis=1, how='all')
            dfs.append(df_mid)
    if dfs:
        team_player_stats = pd.concat(dfs, ignore_index=True)
        team_player_stats = team_player_stats[team_player_stats['team'] == team_name]
    else:
        team_player_stats = pd.DataFrame()
else:
    team_player_stats = pd.DataFrame()

def get_player_groups(stats_df):
    groups = {}
    for player in stats_df['player_name'].unique():
        pos_series = stats_df.loc[stats_df['player_name'] == player, 'position'].dropna()
        if pos_series.empty:
            groups[player] = []
            continue
        positions = []
        for pos in pos_series:
            positions.extend([p.strip() for p in pos.split(',')])
        total = len(positions)
        group_counts = {}
        position_to_group = {
            "GK": ["Goalkeepers"],
            "DF": ["Centrebacks", "Fullbacks"],
            "CB": ["Centrebacks"],
            "LB": ["Fullbacks"],
            "RB": ["Fullbacks"],
            "LWB": ["Fullbacks", "Wingers"],
            "RWB": ["Fullbacks", "Wingers"],
            "WB": ["Fullbacks", "Wingers"],
            "MF": ["Midfielders"],
            "CM": ["Midfielders"],
            "DM": ["Midfielders"],
            "AM": ["Midfielders", "Forwards"],
            "RM": ["Midfielders", "Wingers"],
            "LM": ["Midfielders", "Wingers"],
            "LW": ["Wingers", "Forwards"],
            "RW": ["Wingers", "Forwards"],
            "FW": ["Forwards"],
            "CF": ["Forwards"],
            "ST": ["Forwards"],
            "SS": ["Forwards"]
        }
        for pos in positions:
            mapped = position_to_group.get(pos)
            if not mapped:
                continue
            for grp in mapped:
                group_counts[grp] = group_counts.get(grp, 0) + 1
        if not group_counts:
            groups[player] = []
        else:
            dominant_grp = max(group_counts, key=lambda g: group_counts[g])
            assigned = {dominant_grp}
            for grp, cnt in group_counts.items():
                if grp != dominant_grp and (cnt / total) >= 0.25:
                    assigned.add(grp)
            groups[player] = list(assigned)
    return groups

precomputed_groups = get_player_groups(team_player_stats)

# Tabs initiation
tab1, tab2, tab3 = st.tabs([
    "Team Analysis",
    "Player Analysis",
    "Match Analysis"
])

##############################################
# TAB 1: Team Analysis
##############################################
with tab1:
    st.header("📊 Team Analysis")

    calculate_and_display_key_team_metrics(df, selected_season, team_name)
    total_wins = df[df['result'] == 'W'].shape[0]
    total_draws = df[df['result'] == 'D'].shape[0]
    total_losses = df[df['result'] == 'L'].shape[0]
    matches_played = total_wins + total_draws + total_losses
    
    gf_values = df['gf'].apply(
        lambda x: float(x.split('(')[0]) if isinstance(x, str) else float(x) if pd.notna(x) else 0.0
    )
    ga_values = df['ga'].apply(
        lambda x: float(x.split('(')[0]) if isinstance(x, str) else float(x) if pd.notna(x) else 0.0
    )
    total_goals_for = gf_values.sum()
    total_goals_against = ga_values.sum()
    total_xG = df['xg_filled'].sum(skipna=True)
    total_xGA = df['xga_filled'].sum(skipna=True)
    
    df_overview = pd.DataFrame({
        "Metric": ["Goals For", "Expected Goals", "Goals Against", "Expected Goals Against"],
        "Value": [total_goals_for / matches_played if matches_played else 0,
                  total_xG / matches_played if matches_played else 0,
                  total_goals_against / matches_played if matches_played else 0,
                  total_xGA / matches_played if matches_played else 0],
        "Category": ["Goals For", "Goals For", "Goals Against", "Goals Against"]
    })
    fig_overview2 = px.bar(
        df_overview,
        x="Metric",
        y="Value",
        color="Category",
        barmode="group",
        title="Team Performance Overview (Averages per match)",
        labels={"Value": "Average per match"},
        color_discrete_map={"Goals For": "steelblue", "Goals Against": "indianred"},
        text='Value'
    )
    fig_overview2.update_traces(textposition='outside', texttemplate='%{text:.2f}')
    st.plotly_chart(fig_overview2, use_container_width=True)
    
    played_matches_sorted = played_matches.sort_values('date')
    fig_line = px.line(
        played_matches_sorted,
        x='date',
        y=['gf_clean', 'ga_clean'],
        markers=True,
        title="Goals Scored and Conceded Over Time",
        hover_data={'opponent': True}
    )
    fig_line.data[0].name = 'Goals Scored'
    fig_line.data[0].line.color = 'steelblue'
    fig_line.data[1].name = 'Goals Conceded'
    fig_line.data[1].line.color = 'indianred'

    st.plotly_chart(fig_line, use_container_width=True)
    
    st.subheader("Aggregate Player Statistics")
    if not team_player_stats.empty:
        # Top scorers plot
        goals_df = (
            team_player_stats.groupby('player_name').agg({
                'performance_gls': 'sum',
                'expected_xg': 'mean',
                'performance_sot': 'sum',
                'minutes_played': 'sum'
            }).reset_index()
        )
        goals_df['performance_sot'] = pd.to_numeric(goals_df['performance_sot'], errors='coerce')
        goals_df = goals_df[goals_df['performance_gls'] >= 1]
        goals_df = goals_df.sort_values('performance_gls', ascending=False).head(10)

        fig_top_scorers = px.bar(
            goals_df,
            x='performance_gls',
            y='player_name',
            orientation='h',
            title="Top Scorers",
            labels={
                'performance_gls': 'Goals', 
                'player_name': 'Player', 
                'performance_sot': 'Shots on target', 
                'minutes_played': 'Minutes played'
            },
            hover_data={'minutes_played': True},
            color='performance_sot',
            color_continuous_scale='Blues',
            text_auto=True
        )
        fig_top_scorers.update_traces(textposition='outside')
        fig_top_scorers.update_layout(
            yaxis={'categoryorder': 'total ascending'},
            height=400
        )
        st.plotly_chart(fig_top_scorers, use_container_width=True)

        # Pass accuracy plot
        passes_df = (
            team_player_stats.groupby('player_name').agg({
                'passes_cmp_percent': 'mean',
                'minutes_played': 'sum',
                'passes_att': 'sum'
            }).reset_index()
        )
        passes_df['passes_att'] = pd.to_numeric(passes_df['passes_att'], errors='coerce')
        passes_df = passes_df[passes_df['minutes_played'] > 500]
        passes_df = passes_df.sort_values('passes_cmp_percent')

        fig_pass_agg = px.bar(
            passes_df,
            x='passes_cmp_percent',
            y='player_name',
            orientation='h',
            title="Pass Accuracy (%) (Aggregate, Players with at least 500 minutes played)",
            labels={
                'passes_cmp_percent': 'Pass Accuracy (%)', 
                'player_name': 'Player', 
                'passes_att': 'Passes attempts', 
                'minutes_played': 'Minutes played'
            },
            hover_data={'minutes_played': True},
            color='passes_att',
            color_continuous_scale='Greens',
            text='passes_cmp_percent'
        )
        fig_pass_agg.update_traces(textposition='outside', texttemplate='%{text:.1f}')
        fig_pass_agg.update_layout(
            yaxis={'categoryorder': 'total ascending'},
            height=600
        )

        st.plotly_chart(fig_pass_agg, use_container_width=True)

        # Dribble Success Rate plot
        dribbles_df = team_player_stats.groupby('player_name').agg({
            'take_ons_att': 'sum',
            'take_ons_succ': 'sum',
            'minutes_played': 'sum'
        }).reset_index()
        dribbles_df['take_ons_att'] = pd.to_numeric(dribbles_df['take_ons_att'], errors='coerce')
        dribbles_df = dribbles_df[dribbles_df['take_ons_att'] >= 20]
        dribbles_df['dribble_success'] = (dribbles_df['take_ons_succ'] / dribbles_df['take_ons_att']) * 100
        dribbles_df = dribbles_df.sort_values('dribble_success', ascending=True)

        fig_dribble = px.bar(
            dribbles_df,
            x='dribble_success',
            y='player_name',
            orientation='h',
            title="Dribble Success Rate (%) (Aggregate, Players with at least 20 attempts)",
            labels={
                'dribble_success': 'Dribble success rate (%)', 
                'player_name': 'Player', 
                'take_ons_att': 'Dribbling attempts', 
                'minutes_played': 'Minutes played'
            },
            hover_data={'minutes_played': True},
            color='take_ons_att',
            color_continuous_scale='Magenta',
            text='dribble_success'
        )
        fig_dribble.update_traces(textposition='outside', texttemplate='%{text:.1f}')
        fig_dribble.update_layout(
            yaxis={'categoryorder': 'total ascending'},
            height=600
        )
    
        st.plotly_chart(fig_dribble, use_container_width=True)

        # Bubble chart: shots, xG per match, goals
        shots_bubble_df = team_player_stats.groupby('player_name').agg({
            'expected_xg': 'mean',
            'performance_gls': 'sum',
            'performance_sh': 'sum'
        }).reset_index()

        shots_bubble_df['group'] = shots_bubble_df['player_name'].apply(
            lambda p: precomputed_groups.get(p, [None])[0] if precomputed_groups.get(p) else "Unknown"
        )

        fig_bubble_gls = px.scatter(
            shots_bubble_df,
            x='expected_xg',
            y='performance_gls',
            size='performance_sh',
            color='group',
            hover_name='player_name',
            hover_data={'player_name': False},
            title="Average xG per match vs Total Goals Scored (Bubble size ~ Shots)",
            labels={
                'expected_xg': 'Average xG per match',
                'performance_gls': 'Actual goals',
                'group': 'Position group',
                'performance_sh': 'Total shots'
            },
            text='player_name'
        )
        fig_bubble_gls.update_traces(textposition='top center')
        st.plotly_chart(fig_bubble_gls, use_container_width=True)
        
        # Bubble chart: passes, xAG per match, assists
        passes_bubble_df = team_player_stats.groupby('player_name').agg({
            'expected_xag': 'mean',
            'performance_ast': 'sum',
            'passes_att': 'sum'
        }).reset_index()
        passes_bubble_df['passes_att'] = pd.to_numeric(passes_bubble_df['passes_att'], errors='coerce')
        passes_bubble_df['group'] = passes_bubble_df['player_name'].apply(
            lambda p: precomputed_groups.get(p, [None])[0] if precomputed_groups.get(p) else "Unknown"
        )

        fig_bubble_ast = px.scatter(
            passes_bubble_df,
            x='expected_xag',
            y='performance_ast',
            size='passes_att',
            color='group',
            hover_name='player_name',
            hover_data={'player_name': False},
            title="Average xAG per match vs Total Assists Provided (Bubble size ~ Passes Attempted)",
            labels={
                'expected_xag': 'Average xAG per match',
                'performance_ast': 'Actual assists',
                'group': 'Position group',
                'passes_att': 'Total passes'
            },
            text='player_name'
        )
        fig_bubble_ast.update_traces(textposition='top center')

        st.plotly_chart(fig_bubble_ast, use_container_width=True)

        # Average progressive passes and carries per match
        match_counts = team_player_stats.groupby('player_name').size().reset_index(name='match_count')

        progressive_df = team_player_stats.groupby('player_name').agg({
            'passes_prgp': 'mean',
            'carries_prgc': 'mean'
        }).reset_index()
        progressive_df['passes_prgp'] = pd.to_numeric(progressive_df['passes_prgp'], errors='coerce')
        progressive_df['carries_prgc'] = pd.to_numeric(progressive_df['carries_prgc'], errors='coerce')
        progressive_df = progressive_df.merge(match_counts, on='player_name')
        min_matches = 5
        progressive_df = progressive_df[progressive_df['match_count'] >= min_matches]
        progressive_df = progressive_df.rename(columns={
            'passes_prgp': 'Avg Progressive Passes',
            'carries_prgc': 'Avg Progressive Carries'
        })

        fig_progressive_stats_grouped = px.bar(
            progressive_df,
            x='player_name',
            y=['Avg Progressive Passes', 'Avg Progressive Carries'],
            barmode='group',
            title="Average Progressive Passes and Carries per match",
            labels={
                'value': 'Average per match',
                'player_name': 'Player',
                'variable': 'Statistic'
            },
            color_discrete_map={
                'Avg Progressive Passes': 'steelblue',
                'Avg Progressive Carries': 'indianred'
            },
            text='value'
        )
        fig_progressive_stats_grouped.update_traces(textposition='outside', texttemplate='%{text:.2f}')
        fig_progressive_stats_grouped.update_layout(
            xaxis={'categoryorder': 'total descending'},
            height=500
        )

        st.plotly_chart(fig_progressive_stats_grouped, use_container_width=True)
    else:
        st.warning("No aggregate player statistics available.")

##############################################
# TAB 2: Player Analysis
##############################################
with tab2:
    st.header("🔍 Player Analysis")
    if not team_player_stats.empty:
        precomputed_groups_local = get_player_groups(team_player_stats)

        group_options = ["Goalkeepers", "Centrebacks", "Fullbacks", "Midfielders", "Wingers", "Forwards"]
        selected_group = st.selectbox("Select Position Group:", group_options, index=0)

        team_group_players = sorted([player for player in team_player_stats['player_name'].unique() 
                                    if selected_group in precomputed_groups_local.get(player, [])])

        with st.form(key="compare_form", clear_on_submit=False, border=False):
            selected_players = st.multiselect("Select players for comparison (from your team):", 
                                                team_group_players, default=None)
            compare_button = st.form_submit_button("Compare")

        if compare_button:
            if not selected_players:
                st.info("No players selected. Please select at least one player.")
            else:
                GK_columns = ["minutes_played", "shot_stopping_sota", "shot_stopping_ga", "shot_stopping_saves",
                                "shot_stopping_save_percent", "shot_stopping_psxg", "launched_cmp", "launched_att",
                                "launched_cmp_percent", "passes_att_gk", "passes_thr", "passes_launch_percent",
                                "passes_avglen", "goal_kicks_att", "goal_kicks_launch_percent", "goal_kicks_avglen",
                                "crosses_opp", "crosses_stp", "crosses_stp_percent", "sweeper_opa", "sweeper_avgdist"]
                field_columns = ["minutes_played", "performance_gls", "performance_ast", "performance_pk", "performance_pkatt",
                                    "performance_sh", "performance_sot", "performance_touches", "performance_int", "performance_tkl",
                                    "performance_blocks", "expected_xg", "expected_npxg", "expected_xag", "sca_sca", "sca_gca",
                                    "passes_cmp", "passes_att", "passes_cmp_percent", "passes_prgp", "carries_carries", "carries_prgc",
                                    "take_ons_att", "take_ons_succ"]
                cols = GK_columns if selected_group == "Goalkeepers" else field_columns

                comp_df = compute_player_per90_stats(team_player_stats, selected_players, cols)
                comp_df = comp_df.round(2)
                comp_df.index.name = "Player"
                st.subheader("Comparison of Selected Players (Per 90 Minutes)")
                st.dataframe(comp_df, use_container_width=True)

                # Definicja metryk, które chcemy prezentować (dla danej grupy)
                group_metrics = {
                    "Goalkeepers": ["shot_stopping_sota", "shot_stopping_ga", "shot_stopping_saves", "shot_stopping_save_percent", "shot_stopping_psxg"],
                    "Centrebacks": ["performance_int", "performance_tkl", "performance_blocks", "passes_cmp", "passes_att", "passes_cmp_percent"],
                    "Fullbacks": ["performance_ast", "expected_xag", "passes_cmp", "passes_att", "passes_cmp_percent", "passes_prgp", "sca_sca", "sca_gca", "performance_tkl", "performance_int"],
                    "Midfielders": ["performance_gls", "performance_ast", "expected_xg", "expected_xag", "passes_cmp", "passes_att", "passes_cmp_percent", "passes_prgp", "sca_sca", "sca_gca"],
                    "Wingers": ["performance_gls", "performance_ast", "expected_xg", "expected_xag", "carries_carries", "carries_prgc", "take_ons_att", "take_ons_succ", "sca_sca", "sca_gca"],
                    "Forwards": ["performance_gls", "performance_ast", "expected_xg", "expected_xag", "performance_sh", "performance_sot", "sca_sca", "sca_gca"],
                }
                # Wybrane metryki dla wybranej grupy
                selected_metrics = group_metrics.get(selected_group, [])

                # Wyodrębniamy z obliczonego DataFrame tylko kolumny odpowiadające metrykom dla wykresu
                comp_df_filtered = comp_df[selected_metrics].copy()
                comp_df_filtered.index.name = "Player"
                comp_df_filtered = comp_df_filtered.reset_index()
                comp_df_filtered = comp_df_filtered.round(2)
                # Opcjonalnie: mapowanie nazw metryk na przyjazne etykiety
                friendly_labels = {
                    "shot_stopping_sota": "Shots on Target Against",
                    "shot_stopping_ga": "Goals Conceded",
                    "shot_stopping_saves": "Saves",
                    "shot_stopping_save_percent": "Save %",
                    "shot_stopping_psxg": "PSxG",
                    "performance_gls": "Goals",
                    "performance_ast": "Assists",
                    "expected_xg": "Expected Goals",
                    "expected_xag": "Expected Assists",
                    "performance_int": "Interceptions",
                    "performance_tkl": "Tackles",
                    "performance_blocks": "Blocks",
                    "passes_cmp": "Passes Completed",
                    "passes_att": "Passes Attempted",
                    "passes_cmp_percent": "Pass Completion (%)",
                    "passes_prgp": "Progressive Passes",
                    "sca_sca": "SCA",
                    "sca_gca": "GCA",
                    "carries_carries": "Carries",
                    "carries_prgc": "Progressive Carries",
                    "take_ons_att": "Dribble Attempts",
                    "take_ons_succ": "Successful Dribbles"
                }
                comp_df_filtered = comp_df_filtered.rename(columns=lambda col: friendly_labels.get(col, col))

                # Propozycja wykresu: Small multiples – dla każdej metryki tworzymy osobny wykres słupkowy
                st.subheader("Per 90 Minutes Statistics by Metric")
                for metric in comp_df_filtered.columns:
                    if metric == "Player":
                        continue
                    fig = px.bar(
                        comp_df_filtered,
                        x=metric,
                        y="Player",
                        orientation="h",
                        title=f"Comparison for {metric}",
                        labels={metric: f"{metric}", "Player": "Player"}
                    )
                    fig.update_traces(texttemplate='%{x:.2f}', textposition='outside')
                    fig.update_layout(yaxis={'categoryorder': 'total ascending'}, height=400)
                    st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No individual player statistics available.")

##############################################
# TAB 3: Match Analysis
##############################################
with tab3:
    st.header("📋 Match Analysis")
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        played_matches = df[df['result'].notna()]
        future_matches = df[df['result'].isna()].sort_values(by='date')
        next_match = future_matches.iloc[:1] if not future_matches.empty else pd.DataFrame()
        filtered_matches = pd.concat([played_matches, next_match]).sort_values(by='date')
        match_options = filtered_matches.apply(
            lambda row: f"{row['date'].strftime('%Y-%m-%d')} - {row['opponent']} ({row['result'] if pd.notna(row['result']) else 'Upcoming'})",
            axis=1
        ).tolist()
        selected_match = st.selectbox("Select match:", match_options)
        selected_mask = filtered_matches.apply(
            lambda row: f"{row['date'].strftime('%Y-%m-%d')} - {row['opponent']} ({'Upcoming' if pd.isna(row['result']) else row['result']})",
            axis=1
        ) == selected_match

        if not selected_mask.any():
            st.error("Match not found.")
        else:
            match_row = filtered_matches[selected_mask].iloc[0]
            match_id = match_row['id']
            
            # Jeżeli mecz jest nadchodzący (brak wyniku), proponujemy wyjściową jedenastkę
            if pd.isna(match_row['result']):
                st.subheader("Proposed Starting Eleven for Upcoming Match")
                # Pobieramy ostatnie rozegrane mecze (np. ostatnie 3 mecze) – funkcje te muszą być zaimplementowane
                recent_matches = get_recent_matches(team_id, n=3)
                # Obliczamy statystyki per 90 minut na podstawie ostatnich meczów
                if recent_matches.empty:
                    st.warning("Not enough recent matches to compute player stats.")
                else:
                    team_stats_recent = compute_recent_player_stats(team_id, recent_matches)
                    # Wybierz formację – przykładowo "433"
                    formation = formations["433"]
                    starting_eleven = propose_starting_eleven(team_stats_recent, formation, metrics_per_position)
                    if starting_eleven:
                        output_lines = []
                        for i, (pos_key, player) in enumerate(starting_eleven, start=1):
                            # Usuń numerację z pozycji, np. "GK_1" -> "GK"
                            pos = pos_key.split("_")[0]
                            player_str = player if player is not None else "No selection"
                            output_lines.append(f"{i}. {pos} - {player_str}")
                        st.markdown("\n".join(output_lines))
                    else:
                        st.info("No eligible players for the proposed lineup.")
            else:
                match_stats = get_players_stats(match_id)
                our_stats = match_stats[match_stats['team'] == team_name]
                opp_stats = match_stats[match_stats['team'] != team_name]
                
                st.subheader("Key Statistics Comparision")
                if not our_stats.empty and not opp_stats.empty:
                    try:
                        match_row = df[df['id'] == match_id].iloc[0]
                        our_possession = float(match_row['possession'])
                    except:
                        our_possession = None
                    opp_possession = 100 - our_possession if our_possession is not None else None

                    our_total_goals = our_stats['performance_gls'].sum()
                    opp_total_goals = opp_stats['performance_gls'].sum()

                    our_expected_xg = our_stats['expected_xg'].sum()
                    opp_expected_xg = opp_stats['expected_xg'].sum()

                    our_shots = our_stats['performance_sh'].sum()
                    opp_shots = opp_stats['performance_sh'].sum()

                    our_shots_on_target = our_stats['performance_sot'].sum()
                    opp_shots_on_target = opp_stats['performance_sot'].sum()

                    our_pass_att = our_stats['passes_att'].sum()
                    opp_pass_att = opp_stats['passes_att'].sum()

                    our_pass_cmp = our_stats['passes_cmp'].sum()
                    opp_pass_cmp = opp_stats['passes_cmp'].sum()

                    our_pass_accuracy = (our_pass_cmp / our_pass_att * 100) if our_pass_att > 0 else None
                    opp_pass_accuracy = (opp_pass_cmp / opp_pass_att * 100) if opp_pass_att > 0 else None

                    our_performance_blocks = our_stats['performance_blocks'].sum()
                    opp_performance_blocks = opp_stats['performance_blocks'].sum()

                    our_shot_stopping_saves = our_stats['shot_stopping_saves'].sum()
                    opp_shot_stopping_saves = opp_stats['shot_stopping_saves'].sum()

                    our_performance_tkl = our_stats['performance_tkl'].sum()
                    opp_performance_tkl = opp_stats['performance_tkl'].sum()

                    our_performance_int = our_stats['performance_int'].sum()
                    opp_performance_int = opp_stats['performance_int'].sum()

                    comparison_data = {
                        "Metric": [
                            "Goals",
                            "Expected Goals",
                            "Shots",
                            "Shots on Target",
                            "Possession",
                            "Pass Accuracy",
                            "Passes Attempted",
                            "Passes Completed",
                            "Blocks",
                            "Goalkeeper Saves",
                            "Tackles",
                            "Interceptions"
                        ],
                        "HomeValue": [
                            our_total_goals,
                            our_expected_xg,
                            our_shots,
                            our_shots_on_target,
                            our_possession,
                            our_pass_accuracy,
                            our_pass_att,
                            our_pass_cmp,
                            our_performance_blocks,
                            our_shot_stopping_saves,
                            our_performance_tkl,
                            our_performance_int
                        ],
                        "AwayValue": [
                            opp_total_goals,
                            opp_expected_xg,
                            opp_shots,
                            opp_shots_on_target,
                            opp_possession,
                            opp_pass_accuracy,
                            opp_pass_att,
                            opp_pass_cmp,
                            opp_performance_blocks,
                            opp_shot_stopping_saves,
                            opp_performance_tkl,
                            opp_performance_int
                        ]
                    }
                    comparison_df = pd.DataFrame(comparison_data)

                    def compute_ratio(home_val, away_val):
                        if home_val is None or pd.isna(home_val):
                            home_val = 0.0
                        if away_val is None or pd.isna(away_val):
                            away_val = 0.0
                        total = home_val + away_val
                        if total == 0:
                            return 0.0, 0.0
                        ratio_home = (home_val / total) * 100
                        ratio_away = (away_val / total) * 100
                        return ratio_home, ratio_away

                    ratios_home = []
                    ratios_away = []
                    for idx, row in comparison_df.iterrows():
                        rh, ra = compute_ratio(row["HomeValue"], row["AwayValue"])
                        ratios_home.append(rh)
                        ratios_away.append(ra)

                    comparison_df["HomeRatio"] = ratios_home
                    comparison_df["AwayRatio"] = ratios_away
                    comparison_df["HomeRatioNeg"] = -comparison_df["HomeRatio"]

                    comparison_df["HomeColor"] = comparison_df.apply(
                        lambda row: "gray" if row["HomeValue"] == row["AwayValue"] 
                                    else ("forestgreen" if row["HomeValue"] > row["AwayValue"] else "indianred"), axis=1)
                    comparison_df["AwayColor"] = comparison_df.apply(
                        lambda row: "gray" if row["HomeValue"] == row["AwayValue"] 
                                    else ("forestgreen" if row["AwayValue"] > row["HomeValue"] else "indianred"), axis=1)

                    def format_value(metric, value):
                        if metric == "Expected Goals":
                            return f"{value:.1f}"
                        else:
                            return f"{value:.0f}"

                    comparison_df["HomeText"] = comparison_df.apply(lambda row: format_value(row["Metric"], row["HomeValue"]), axis=1)
                    comparison_df["AwayText"] = comparison_df.apply(lambda row: format_value(row["Metric"], row["AwayValue"]), axis=1)

                    fig_butterfly = go.Figure()

                    fig_butterfly.add_trace(go.Bar(
                        y=comparison_df["Metric"],
                        x=comparison_df["HomeRatioNeg"],
                        orientation='h',
                        name="",
                        text=comparison_df["HomeText"],
                        textposition='inside',
                        marker_color=comparison_df["HomeColor"].tolist()
                    ))

                    fig_butterfly.add_trace(go.Bar(
                        y=comparison_df["Metric"],
                        x=comparison_df["AwayRatio"],
                        orientation='h',
                        name="",
                        text=comparison_df["AwayText"],
                        textposition='inside',
                        marker_color=comparison_df["AwayColor"].tolist()
                    ))

                    fig_butterfly.update_layout(
                        barmode='relative',
                        xaxis=dict(
                            range=[-100, 100],
                            showgrid=False,
                            zeroline=True,
                            zerolinecolor='black',
                            zerolinewidth=1,
                            showticklabels=False  # Ukrywamy etykiety osi X
                        ),
                        yaxis=dict(
                            automargin=True,
                            categoryorder='array',
                            categoryarray=comparison_df["Metric"][::-1]  # Odwrócona kolejność metryk
                        ),
                        showlegend=False,
                        height=600
                    )

                    fig_butterfly.update_traces(
                        texttemplate='%{text}',
                        insidetextanchor='start',
                        textfont=dict(
                            size=16,
                            color="white",
                            weight="bold"
                        )
                    )
                    fig_butterfly.add_annotation(
                        dict(
                            x=0.0, y=1.1,
                            xref="paper", yref="paper",
                            text=team_name,  
                            showarrow=False,
                            font=dict(size=32, weight="bold")
                        )
                    )
                    fig_butterfly.add_annotation(
                        dict(
                            x=1.0, y=1.1,
                            xref="paper", yref="paper",
                            text="Opponent",
                            showarrow=False,
                            font=dict(size=32, weight="bold")
                        )
                    )
                    st.plotly_chart(fig_butterfly, use_container_width=True)

                    # Our team plots
                    fig_match1 = px.bar(
                        our_stats,
                        x='player_name',
                        y=['performance_sh', 'performance_sot'],
                        barmode='group',
                        title="Shots vs Shots on Target (Our Team)",
                        labels={'value': 'Count', 'variable': 'Metric', 'player_name': 'Player'},
                        color_discrete_sequence=px.colors.qualitative.Set1
                    )
                    st.plotly_chart(fig_match1, use_container_width=True)
                    
                    goals_assists = our_stats.groupby('player_name').agg({
                        'performance_gls': 'sum',
                        'performance_ast': 'sum'
                    }).reset_index()
                    fig_match2 = px.bar(
                        goals_assists,
                        x='player_name',
                        y=['performance_gls', 'performance_ast'],
                        barmode='group',
                        title="Goals and Assists per Player (Our Team)",
                        labels={'value': 'Count', 'variable': 'Metric', 'player_name': 'Player'},
                        color_discrete_sequence=px.colors.qualitative.Pastel
                    )
                    st.plotly_chart(fig_match2, use_container_width=True)
                    
                    passes_data = our_stats.groupby('player_name').agg({'passes_cmp': 'sum'}).reset_index()
                    fig_match3 = px.pie(
                        passes_data,
                        names='player_name',
                        values='passes_cmp',
                        title="Distribution of Completed Passes (Our Team)"
                    )
                    st.plotly_chart(fig_match3, use_container_width=True)
                    
                    if not opp_stats.empty:
                        our_agg = our_stats.agg({
                            'performance_sh': 'sum',
                            'performance_sot': 'sum',
                            'performance_gls': 'sum'
                        })
                        opp_agg = opp_stats.agg({
                            'performance_sh': 'sum',
                            'performance_sot': 'sum',
                            'performance_gls': 'sum'
                        })
                        metrics = ['Shots', 'Shots on Target', 'Goals']
                        our_values = [our_agg['performance_sh'], our_agg['performance_sot'], our_agg['performance_gls']]
                        opp_values = [opp_agg['performance_sh'], opp_agg['performance_sot'], opp_agg['performance_gls']]
                        df_compare = pd.DataFrame({
                            'Metric': metrics,
                            team_name: our_values,
                            'Opponent': opp_values
                        })
                        fig_match4 = px.bar(
                            df_compare,
                            x='Metric',
                            y=[team_name, 'Opponent'],
                            barmode='group',
                            title="Aggregated Match Metrics: Our Team vs Opponent",
                            labels={'value': 'Total Count'}
                        )
                        st.plotly_chart(fig_match4, use_container_width=True)
                else:
                    st.warning("No player statistics available for this match.")
    else:
        st.warning("There are no matches available for this team in the selected season.")