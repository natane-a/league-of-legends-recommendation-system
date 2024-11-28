import os
import json
import requests
import time
import datetime

def load_api_key():
    """
    Load the API key from the credentials file.
    """
    with open("../config/credentials.json", 'r') as f:
        data = json.load(f)
    return data.get("riot_api_key")

def fetch_match_details(api_key, match_id, region):
    """
    Fetch raw match data from Riot API.
    """
    url = f"https://{region}.api.riotgames.com/lol/match/v5/matches/{match_id}"
    headers = {"X-Riot-Token": api_key}

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def fetch_match_timeline(api_key, match_id, region):
    """
    Fetch match timeline data from Riot API.
    """
    url = f"https://{region}.api.riotgames.com/lol/match/v5/matches/{match_id}/timeline"
    headers = {"X-Riot-Token": api_key}

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def extract_match_details(match_data, timeline_data):
    """
    Extract relevant match details from the match data and match timeline.
    """
    participants = match_data['info']['participants']
    extracted_data = []

    for participant in participants:
        # Find the corresponding matchup champion
        matchup_champion = next((p['championName'] for p in participants 
                                 if p['individualPosition'] == participant['individualPosition'] and 
                                 p['teamId'] != participant['teamId']), None)

        # Initialize item purchase times with "Unknown Time"
        item_purchase_times = {f"item_purchase_time_{i}": "Unknown Time" for i in range(6)}

        # Extract item purchase times from the timeline
        participant_id = participant["participantId"]
        for frame in timeline_data["info"]["frames"]:
            for event in frame["events"]:
                if (
                    event["type"] == "ITEM_PURCHASED" and
                    event["participantId"] == participant_id
                ):
                    item_id = event["itemId"]
                    timestamp = event["timestamp"] // 1000  # Convert milliseconds to seconds

                    # Find the appropriate item slot
                    for i in range(6):
                        if participant.get(f"item{i}") == item_id:
                            item_purchase_times[f"item_purchase_time_{i}"] = timestamp
                            break

        # Extract rune data (perks)
        perks = participant.get("perks", {}).get("styles", [])
        primary_rune = perks[0] if len(perks) > 0 else {}
        secondary_rune = perks[1] if len(perks) > 1 else {}

        match_summary = {
            "matchId": match_data["metadata"]["matchId"],
            "gameDuration": match_data["info"]["gameDuration"],
            "championId": participant["championId"],
            "championName": participant["championName"],
            "teamId": participant["teamId"],
            "individualPosition": participant.get("individualPosition", "Unknown"),
            "kills": participant["kills"],
            "deaths": participant["deaths"],
            "assists": participant["assists"],
            "win": participant["win"],
            "goldEarned": participant["goldEarned"],
            "totalDamageDealt": participant["totalDamageDealtToChampions"],
            "totalDamageTaken": participant["totalDamageTaken"],
            "totalHeal": participant["totalHeal"],
            "matchupChampion": matchup_champion,
            "primaryRune": primary_rune,
            "secondaryRune": secondary_rune
        }

        # Add items and their purchase times as individual columns
        for i in range(6):
            item_key = f"item{i}"
            match_summary[f"item_{i}"] = participant.get(item_key, "Unknown Item")
            match_summary[f"item_purchase_time_{i}"] = item_purchase_times[f"item_purchase_time_{i}"]

        extracted_data.append(match_summary)

    return extracted_data

# Load API Key and Set Up Paths
API_KEY = load_api_key()
REGION = "americas"
MATCH_IDS_PATH = "../data/raw/match_ids/match_ids.json"
MATCH_DETAILS_OUTPUT_DIR = "../data/raw/match_details/"

# Ensure the output directory exists
os.makedirs(MATCH_DETAILS_OUTPUT_DIR, exist_ok=True)

# Load match IDs
if os.path.exists(MATCH_IDS_PATH):
    with open(MATCH_IDS_PATH, 'r') as f:
        match_ids = json.load(f)
else:
    match_ids = []

# Find the latest match details file or create the first one
existing_files = [f for f in os.listdir(MATCH_DETAILS_OUTPUT_DIR) if f.startswith("all_match_details") and f.endswith(".json")]
existing_files.sort()

processed_match_ids = set()

# Load all existing match IDs to avoid duplicates
for existing_file in existing_files:
    with open(os.path.join(MATCH_DETAILS_OUTPUT_DIR, existing_file), 'r') as f:
        existing_data = json.load(f)
        processed_match_ids.update([match["matchId"] for match in existing_data])

if existing_files:
    latest_file_number = len(existing_files)
    latest_file = f"all_match_details{latest_file_number:02d}.json"
    all_match_details = []
else:
    latest_file_number = 1
    latest_file = "all_match_details01.json"
    all_match_details = []

# Process each match ID and extract details
request_count = 0
start_time = datetime.datetime.now()

for match_id in match_ids:
    # Skip if match ID has already been processed
    if match_id in processed_match_ids:
        continue

    while True:
        try:
            # Check request rate limits
            current_time = datetime.datetime.now()
            elapsed_seconds = (current_time - start_time).total_seconds()

            if request_count >= 50 and elapsed_seconds < 120:
                sleep_time = 120 - elapsed_seconds
                print(f"Approaching 2-minute rate limit. Waiting for {sleep_time:.2f} seconds...")
                time.sleep(sleep_time)
                request_count = 0
                start_time = datetime.datetime.now()

            # If 10 requests made in the last second, wait for the next second
            if request_count % 10 == 0 and request_count > 0:
                print("10 requests made in the last second. Pausing for 1 second to avoid limit...")
                time.sleep(1)

            # Fetch match details and timeline
            match_data = fetch_match_details(API_KEY, match_id, REGION)
            timeline_data = fetch_match_timeline(API_KEY, match_id, REGION)

            # Extract relevant details
            extracted_details = extract_match_details(match_data, timeline_data)

            # Append new match details to the existing data
            all_match_details.extend(extracted_details)

            # Check if the file exceeds 10,000 entries
            if len(all_match_details) >= 10000:
                # Save the current file and start a new one
                with open(os.path.join(MATCH_DETAILS_OUTPUT_DIR, latest_file), 'w') as f:
                    json.dump(all_match_details[:10000], f, indent=4)
                print(f"Saved {latest_file} with 10,000 entries.")

                # Update the list of remaining details
                all_match_details = all_match_details[10000:]

                # Increment the file name
                latest_file_number += 1
                latest_file = f"all_match_details{latest_file_number:02d}.json"

            # Save the current details to the latest file
            with open(os.path.join(MATCH_DETAILS_OUTPUT_DIR, latest_file), 'w') as f:
                json.dump(all_match_details, f, indent=4)

            print(f"Details for match {match_id} processed and saved to JSON.")
            request_count += 2  # Increment by 2 due to two requests (details and timeline)
            break

        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
            if "expired" in str(e).lower():
                API_KEY = input("API key expired. Please enter a new API key: ")
            else:
                break

print("All match details have been processed.")
