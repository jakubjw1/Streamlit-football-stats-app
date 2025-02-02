import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from io import StringIO
import re
import time
import random
import logging

BASE_FBREF_URL = "https://fbref.com"
    
def scrap_team_matchlogs(team_url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    }

    max_retries = 3 
    retry_delay = 30

    for attempt in range(max_retries):
        try:
            session = requests.Session()
            response = session.get(team_url, headers=headers)

            if response.status_code == 429:
                logging.warning(f"❌ HTTP 429 Too Many Requests. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2 
                continue

            if response.status_code != 200:
                logging.error(f"Unable to retrieve data. HTTP Status Code: {response.status_code}")
                return 

            soup = BeautifulSoup(response.text, "html.parser")

            # Find the table with matchlogs
            matchlogs_table = soup.find('table', {'id': 'matchlogs_for'})
            if matchlogs_table is None:
                logging.warning("Matchlogs table not found in the HTML.")
                return []

            df = pd.read_html(StringIO(str(matchlogs_table)))[0]

            # Extract all 'Match Report' links
            links_elements = matchlogs_table.find_all('td', {'data-stat': 'match_report'})
            match_report_links = [
                BASE_FBREF_URL + td.find('a')['href'] if td.find('a') else None
                for td in links_elements
            ]

            df['match_report_link'] = match_report_links

            # Map columns to database fields
            df.rename(columns={
                'Date': 'date',
                'Time': 'time',
                'Comp': 'competition',
                'Round': 'round',
                'Day': 'day',
                'Venue': 'venue',
                'Opponent': 'opponent',
                'Result': 'result',
                'GF': 'gf',
                'GA': 'ga',
                'xG': 'xg',
                'xGA': 'xga',
                'Poss': 'possession',
                'Attendance': 'attendance',
                'Captain': 'captain',
                'Formation': 'formation',
                'Opp Formation': 'opponent_formation',
                'Referee': 'referee',
                'Notes': 'notes'
            }, inplace=True)

            # Replace NaN with None
            df = df.where(pd.notnull(df), None).drop(columns=['Match Report'])

            # Convert DataFrame to list of dictionaries
            match_data = df.to_dict(orient='records')

            delay = random.uniform(6, 8)
            time.sleep(delay)

            return match_data
        except Exception as e:
            logging.error(f"Error fetching match data: {e}")
            return

def scrap_match_stats(match_url, home_team, away_team, venue):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    }

    max_retries = 3 
    retry_delay = 30

    for attempt in range(max_retries):
        try:
            session = requests.Session()
            response = session.get(match_url, headers=headers)

            if response.status_code == 429:
                logging.warning(f"❌ HTTP 429 Too Many Requests. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2 
                continue

            if response.status_code != 200:
                logging.error(f"Unable to retrieve match report. HTTP Status Code: {response.status_code}")
                return pd.DataFrame(), pd.DataFrame()

            soup = BeautifulSoup(response.text, "html.parser")

            field_players_stats = soup.find_all('table', id=re.compile(r'^stats_.*_summary$'))
            keepers_stats = soup.find_all('table', id=re.compile(r'^keeper_stats_.*'))

            if not field_players_stats:
                logging.warning(f"No player stats found for {home_team} vs {away_team}")
            if not keepers_stats:
                logging.warning(f"No keeper stats found for {home_team} vs {away_team}")

            labels, keepers_labels = [], []
            if venue == "Home":
                labels = [f"{home_team} player stats table", f"{away_team} player stats table"]
                keepers_labels = [f"{home_team} keeper stats table", f"{away_team} keeper stats table"]
            elif venue == "Away":
                labels = [f"{away_team} player stats table", f"{home_team} player stats table"]
                keepers_labels = [f"{away_team} keeper stats table", f"{home_team} keeper stats table"]

            field_players_stats_df, keepers_stats_df = [], []

            # Process field players' stats
            for table, label in zip(field_players_stats, labels):
                try:
                    df = pd.read_html(StringIO(str(table)))[0]
                    if df.empty:
                        logging.warning(f"Empty table for {label}")
                        continue

                    df = df.iloc[:-1, :]  # Drop summary row
                    df.columns = ['_'.join(col).strip() if isinstance(col, tuple) else col.replace(' ', '_').strip() for col in df.columns]
                    df.rename(columns={
                        df.columns[0]: 'Player',
                        df.columns[1]: 'Shirt #',
                        df.columns[2]: 'Nat',
                        df.columns[3]: 'Pos',
                        df.columns[4]: 'Age',
                        df.columns[5]: 'Min'
                    }, inplace=True)

                    # Assign team to each player
                    df['Team'] = home_team if label.startswith(home_team) else away_team
                    field_players_stats_df.append(df)
                except ValueError as e:
                    logging.error(f"Error reading HTML for {label}: {e}")

            # Process keepers' stats
            for table, label in zip(keepers_stats, keepers_labels):
                try:
                    df = pd.read_html(StringIO(str(table)))[0]
                    df.columns = ['_'.join(col).strip() if isinstance(col, tuple) else col.replace(' ', '_').strip() for col in df.columns]
                    df.rename(columns={
                        df.columns[0]: 'Player',
                        df.columns[1]: 'Nat',
                        df.columns[2]: 'Age',
                        df.columns[3]: 'Min'
                    }, inplace=True)

                    # Assign team to each keeper
                    df['Team'] = home_team if label.startswith(home_team) else away_team
                    keepers_stats_df.append(df)
                except ValueError as e:
                    logging.error(f"Error reading HTML for {label}: {e}")

            field_players_stats_df = pd.concat(field_players_stats_df) if field_players_stats_df else pd.DataFrame()
            keepers_stats_df = pd.concat(keepers_stats_df) if keepers_stats_df else pd.DataFrame()

            delay = random.uniform(6, 8)
            time.sleep(delay)

            return field_players_stats_df, keepers_stats_df
        except Exception as e:
            logging.error(f"An error occurred while getting data: {e}")
            return pd.DataFrame(), pd.DataFrame()