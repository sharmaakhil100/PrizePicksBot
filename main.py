import os
import requests
from nba_api.stats.static import players, teams
from nba_api.stats.endpoints import playergamelog, commonplayerinfo
from datetime import datetime
from openai import OpenAI
import pytz  # If you need timezone handling
import json


# Helper function to map team ID to team name
def get_player_team(player_name):
  player_info = players.find_players_by_full_name(player_name)
  if not player_info:
    return None  # No player found
  player_id = player_info[0]['id']

  # Get detailed player information
  player_details = commonplayerinfo.CommonPlayerInfo(player_id=player_id)
  player_data = player_details.get_normalized_dict()
  team_name = player_data['CommonPlayerInfo'][0]['TEAM_NAME']
  team_city = player_data['CommonPlayerInfo'][0]['TEAM_CITY']
  return f"{team_city} {team_name}"


# Function to get today's games mapping teams to their opponents
def get_games():
  games_dict = {}
  url = 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard'
  response = requests.get(url)
  if response.status_code == 200:
    data = response.json()
    for event in data['events']:
      full_matchup_name = event['name']
      team1, team2 = full_matchup_name.split(' at ')
      games_dict[team1.strip()] = team2.strip()
      games_dict[team2.strip()] = team1.strip()
  return games_dict


# Function to get player stats against a specific team
def get_player_stats_against_team(player_name,
                                  opponent_name,
                                  metric_type,
                                  season='2023-24'):
  player_info = players.find_players_by_full_name(player_name)
  if not player_info:
    return "Player not found", None
  player_id = player_info[0]['id']

  team_info = teams.find_teams_by_full_name(opponent_name)
  if not team_info:
    return "Team not found", None
  opponent_abbreviation = team_info[0]['abbreviation']

  gamelog = playergamelog.PlayerGameLog(player_id=player_id, season=season)
  df = gamelog.get_data_frames()[0]
  df_opponent = df[df['MATCHUP'].str.contains(opponent_abbreviation)]

  if metric_type.upper() not in df_opponent.columns:
    return f"Metric type '{metric_type}' not found.", None

  if not df_opponent.empty:
    average_metric = df_opponent[metric_type.upper()].astype(float).mean()
  else:
    return "No matching games found.", None

  return df_opponent, average_metric


# Function to analyze a bet slip
def analyze_NBA_bet_slip(slip):
  """
    Analyze a sports bet (NBA) slip and provide insights.

    :param slip: A string containing the bet slip text. 
                 Ex: 'Luka Doncic OVER 44.5 PRA'
    :return analysis: A string containing the slip analysis. 
  """
  client = OpenAI(api_key=os.environ['OpenAI_Key'])

  response = client.chat.completions.create(
      model="gpt-4-turbo-2024-04-09",
      response_format={"type": "json_object"},
      messages=[
          {
              "role":
              "system",
              "content":
              ("Given a description of a sports bet, extract and format the player's name, "
               "the over/under, the numerical value associated with the bet, and the type "
               "of bet (e.g., points, assists, rebounds, rebounds and assists, points rebounds "
               "and assists, turnovers, 3-points, etc) into a JSON structure. PRA translates to "
               "points rebounds and assists. Similarly, RA translates to rebounds and assists or "
               "PA translates to points and assists etc. Here's an example input and how the output "
               "should be structured: Input: 'LeBron James OVER 27.5 pts.' Output should be formatted as: "
               "{'player_name': 'LeBron James', 'over_or_under': 'over', 'numerical_value': 27.5, 'type_of_bet': 'points'}"
               ),
          },
          {
              "role": "user",
              "content": slip,
          },
      ])

  # Assuming the response is correctly formatted as JSON
  bet_details = json.loads(response.choices[0].message.content)
  # print(bet_details)
  if (bet_details['type_of_bet'].lower()) == "points":
    bet_details['type_of_bet'] = "PTS"
  player_team = get_player_team(bet_details['player_name'])

  if not player_team:
    return "Player team not found or player does not have a game today."

  games_today = get_games()
  opponent_team = games_today.get(player_team)

  if not opponent_team:
    return "No game found for this player today."

  stats, avg_metric = get_player_stats_against_team(bet_details['player_name'],
                                                    opponent_team,
                                                    bet_details['type_of_bet'])

  if avg_metric is None:
    return "Unable to compute average metric."

  return (
      f"{bet_details['player_name']} is expected to score {'over' if avg_metric > bet_details['numerical_value'] else 'under'} "
      f"{bet_details['numerical_value']} {bet_details['type_of_bet']} against {opponent_team}, based on past games, with an average of {avg_metric:.2f} {bet_details['type_of_bet']}."
  )


# Example usage:
print(analyze_NBA_bet_slip("Luka Doncic OVER 25.5 pts"))
