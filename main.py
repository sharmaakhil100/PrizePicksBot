import os
import pandas as pd
import requests
import json
import pytz  # To handle timezone differences
from datetime import datetime
from nba_api.stats.endpoints import playergamelog
from nba_api.stats.static import players, teams
from openai import OpenAI

client = OpenAI(api_key=os.environ['OpenAI_Key'])

# response = client.chat.completions.create(
#     model="gpt-4-turbo-2024-04-09",
#     response_format={"type": "json_object"},
#     messages=[
#         {
#             "role":
#             "system",
#             "content":
#             "Given a description of a sports bet, extract and format the player's name, the over/under, the numerical value associated with the bet, and the type of bet (e.g., points, assists, rebounds, rebounds and assists, points rebounds and assists, turnovers, 3-points, etc) into a JSON structure. PRA transates to points rebounds and assists. Similarly, RA translates to rebounds and assists or PA translates to points and assists etc. Here's an example input and how the output should be structured: Input: 'LeBron James OVER 27.5 pts.' Output should be formatted as: {'player_name': 'LeBron James', 'over_or_under': 'over', 'numerical_value': 27.5, 'type_of_bet': 'points'}",
#         },
#         {
#             "role": "user",
#             "content": "Luka Doncic over 34.5 PA",
#         },
#     ])

# print(response.choices[0].message.content)


def get_games():
  """
  This function gets the games for a given date.
  
  return: dictionary containing the games for today's date! 
  """
  games_dict = {}
  url = 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard'
  response = requests.get(url)

  if response.status_code == 200:
    data = response.json()
    print("Received data:")

    for d in data['events']:
      full_matchup_name = d['name']
      print(full_matchup_name)
      team1, team2 = full_matchup_name.split(' at ')
      # team1, team2 = team1.strip(), team2.strip()
      games_dict[team1] = team2
      games_dict[team2] = team1
      # print(f"{d['name']}, {d['shortName']}")
    # print(data['events'])
  else:
    print(f"Failed to retrieve data. Status code: {response.status_code}")
  return games_dict


def get_player_stats_against_team(player_name,
                                  opponent_name,
                                  metric_type,
                                  season='2023-24'):
  # Find player by name
  player_dict = players.find_players_by_full_name(player_name)
  if not player_dict:
    return "Player not found"
  player_id = player_dict[0]['id']

  # Find opponent team by name
  team_dict = teams.find_teams_by_full_name(opponent_name)
  if not team_dict:
    return "Opponent team not found"
  opponent_abbreviation = team_dict[0]['abbreviation']  # Use team abbreviation

  # Fetch player game log for the season
  gamelog = playergamelog.PlayerGameLog(player_id=player_id, season=season)
  df = gamelog.get_data_frames()[0]

  # Filter games played against the opponent using abbreviation
  df_opponent = df[df['MATCHUP'].str.contains(opponent_abbreviation)]

  # Check if the DataFrame contains the expected metric column
  if metric_type.upper() not in df_opponent.columns:
    return f"Column '{metric_type.upper()}' not found in the data. Available columns: {df_opponent.columns.tolist()}"

  # Calculate the specific metric for each game
  results = df_opponent[[metric_type.upper(), 'GAME_DATE', 'MATCHUP']].copy()
  results.columns = ['Metric', 'Game Date', 'Matchup']

  # Calculate the average of the specified metric
  average_metric = results['Metric'].astype(float).mean()

  return results, average_metric


# Example usage
player_performance, average_points = get_player_stats_against_team(
    "Luka Doncic", "San Antonio Spurs", "PTS")
print(player_performance)
print(f"Average Points Scored: {average_points}")
