import os
import json
import requests
import time
import datetime

def load_api_key():
    """
    load the API key from the credentials file.
    """
    with open("../config/credentials.json", 'r') as f:
        data = json.load(f)
    return data.get("riot_api_key")

def fetch_match_details(api_key, match_id, region):
    """
    fetch raw match data from Riot API.
    """
    url = f"https://{region}.api.riotgames.com/lol/match/v5/matches/{match_id}"
    headers = {"X-Riot-Token": api_key}

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def fetch_match_timeline(api_key, match_id, region):
    """
    fetch match timeline data from Riot API.
    """
    url = f"https://{region}.api.riotgames.com/lol/match/v5/matches/{match_id}/timeline"
    headers = {"X-Riot-Token": api_key}

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def extract_match_details(match_data, timeline_data):
    """
    extract relevant match details from the match data and match timeline.
    """
    participants = match_data['info']['participants']
    extracted_data = []

    for participant in participants:
        # find the corresponding matchup champion
        matchup_champion = next((p['championName'] for p in participants 
                                 if p['individualPosition'] == participant['individualPosition'] and 
                                 p['teamId'] != participant['teamId']), None)

        # initialize item purchase times with unknown time
        item_purchase_times = {f"item_purchase_time_{i}": "Unknown Time" for i in range(6)}

        # extract item purchase times from the timeline
        participant_id = participant["participantId"]
        for frame in timeline_data["info"]["frames"]:
            for event in frame["events"]:
                if (
                    event["type"] == "ITEM_PURCHASED" and
                    event["participantId"] == participant_id
                ):
                    item_id = event["itemId"]
                    timestamp = event["timestamp"] // 1000  # converting milliseconds to seconds

                    # find the appropriate item slot
                    for i in range(6):
                        if participant.get(f"item{i}") == item_id:
                            item_purchase_times[f"item_purchase_time_{i}"] = timestamp
                            break

        # extract rune data 
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

        # add items and their purchase times as individual columns
        for i in range(6):
            item_key = f"item{i}"
            match_summary[f"item_{i}"] = participant.get(item_key, "Unknown Item")
            match_summary[f"item_purchase_time_{i}"] = item_purchase_times[f"item_purchase_time_{i}"]

        extracted_data.append(match_summary)

    return extracted_data

# load API key and set up paths
API_KEY = load_api_key()
REGION = "americas"
MATCH_IDS_PATH = "../data/raw/match_ids/match_ids.json"
MATCH_DETAILS_OUTPUT_DIR = "../data/raw/match_details/"

# ensure the output directory exists
os.makedirs(MATCH_DETAILS_OUTPUT_DIR, exist_ok=True)

# load match ids
if os.path.exists(MATCH_IDS_PATH):
    with open(MATCH_IDS_PATH, 'r') as f:
        match_ids = json.load(f)
else:
    match_ids = []

# find the latest match details file or create the first one
existing_files = [f for f in os.listdir(MATCH_DETAILS_OUTPUT_DIR) if f.startswith("all_match_details") and f.endswith(".json")]
existing_files.sort()

if existing_files:
    latest_file = existing_files[-1]
    with open(os.path.join(MATCH_DETAILS_OUTPUT_DIR, latest_file), 'r') as f:
        all_match_details = json.load(f)
else:
    latest_file = "all_match_details01.json"
    all_match_details = []

# process each match ID and extract details
request_count = 0
start_time = datetime.datetime.now()

for match_id in match_ids:
    while True:
        try:
            # check request rate limits
            current_time = datetime.datetime.now()
            elapsed_seconds = (current_time - start_time).total_seconds()

            if request_count >= 50 and elapsed_seconds < 120:
                sleep_time = 120 - elapsed_seconds
                print(f"Approaching 2-minute rate limit. Waiting for {sleep_time:.2f} seconds...")
                time.sleep(sleep_time)
                request_count = 0
                start_time = datetime.datetime.now()

            # if 10 requests made in the last second, wait for the next second
            if request_count % 10 == 0 and request_count > 0:
                print("10 requests made in the last second. Pausing for 1 second to avoid limit...")
                time.sleep(1)

            # fetch match details and timeline
            match_data = fetch_match_details(API_KEY, match_id, REGION)
            timeline_data = fetch_match_timeline(API_KEY, match_id, REGION)

            # extract relevant details
            extracted_details = extract_match_details(match_data, timeline_data)

            # append new match details to the existing data
            all_match_details.extend(extracted_details)

            # check if the file exceeds 10,000 entries
            if len(all_match_details) > 10000:
                # save the current file and start a new one
                with open(os.path.join(MATCH_DETAILS_OUTPUT_DIR, latest_file), 'w') as f:
                    json.dump(all_match_details[:10000], f, indent=4)
                print(f"Saved {latest_file} with 10,000 entries.")

                # update the list of remaining details
                all_match_details = all_match_details[10000:]

                # increment the file name
                latest_file_number = int(latest_file[-6:-5]) + 1
                latest_file = f"all_match_details{latest_file_number:02d}.json"

            # save the current details to the latest file
            with open(os.path.join(MATCH_DETAILS_OUTPUT_DIR, latest_file), 'w') as f:
                json.dump(all_match_details, f, indent=4)

            print(f"Details for match {match_id} processed and saved to JSON.")
            request_count += 2  # increment by 2 due to two requests (details and timeline)
            break

        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
            if "expired" in str(e).lower():
                API_KEY = input("API key expired. Please enter a new API key: ")
            else:
                break

print("All match details have been processed.")
