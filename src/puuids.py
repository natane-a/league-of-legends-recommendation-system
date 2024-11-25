import json
import time
import datetime
import requests
import pandas as pd
import os

# path to credentials.json
credentials_path = "../config/credentials.json"

# load API key
with open(credentials_path, 'r') as file:
    credentials = json.load(file)
    api_key = credentials.get("riot_api_key")

def fetch_puuids(api_key, summoner_ids_path, region, output_path):
    """
    Fetch PUUIDs for summoners given their summoner IDs.

    Parameters:
    - api_key: str, your Riot Games API key.
    - summoner_ids_path: str, path to the JSON file containing summoner IDs.
    - region: str, region for summoner data (e.g., "na1").
    - output_path: str, path to save the output JSON file for PUUIDs.

    Returns:
    - puuids: list, list of PUUIDs for all summoners.
    """
    # Load summoner IDs from the given JSON file
    if not os.path.exists(summoner_ids_path):
        print(f"Summoner IDs file not found: {summoner_ids_path}")
        return []

    with open(summoner_ids_path, 'r') as f:
        summoner_data = json.load(f)

    # Combine all summoner IDs from different branches into a single list
    summoner_ids = []
    for rank in summoner_data:
        summoner_ids.extend(summoner_data[rank])

    puuids = []
    headers = {"X-Riot-Token": api_key}

    # Load existing PUUIDs if the output file exists
    if os.path.exists(output_path):
        with open(output_path, 'r') as f:
            existing_puuids = json.load(f)
    else:
        existing_puuids = []

    # Initialize rate limit tracking
    request_count = 0
    start_time = datetime.datetime.now()

    for summoner_id in summoner_ids:
        # Check rate limits
        current_time = datetime.datetime.now()
        elapsed_seconds = (current_time - start_time).total_seconds()

        # Reset the request count after 2 minutes
        if elapsed_seconds > 120:
            request_count = 0
            start_time = current_time

        # If we're approaching the 2-minute limit, wait
        if request_count >= 90:
            sleep_time = 120 - elapsed_seconds
            print(f"Approaching 2-minute rate limit. Waiting for {sleep_time:.2f} seconds...")
            time.sleep(sleep_time)
            request_count = 0
            start_time = datetime.datetime.now()

        # Fetch PUUID using summonerId
        try:
            url = f"https://{region}.api.riotgames.com/lol/summoner/v4/summoners/{summoner_id}"
            response = requests.get(url, headers=headers)
            request_count += 1

            # Rate limit per second (20 requests per second)
            if request_count % 20 == 0:
                print("20 requests made in the last second. Pausing for 1 second to avoid limit...")
                time.sleep(1)

            response.raise_for_status()
            summoner_data = response.json()
            puuid = summoner_data["puuid"]
            if puuid not in existing_puuids and puuid not in puuids:
                puuids.append(puuid)
        except requests.exceptions.RequestException as e:
            print(f"Error fetching PUUID for summonerId {summoner_id}: {e}")
            continue

    # Combine new PUUIDs with existing ones and remove duplicates
    all_puuids = list(set(existing_puuids + puuids))

    # Ensure the output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Save updated PUUIDs to JSON file
    with open(output_path, 'w') as f:
        json.dump(all_puuids, f, indent=4)

    print(f"PUUIDs updated and saved to {output_path}")
    return all_puuids

# Example Usage
API_KEY = api_key
SUMMONER_IDS_PATH = "../data/raw/summoner_id/summoner_id.json"
REGION = "na1"
OUTPUT_PATH = "../data/raw/puuids/puuids.json"

puuids = fetch_puuids(
    api_key=API_KEY, 
    summoner_ids_path=SUMMONER_IDS_PATH, 
    region=REGION, 
    output_path=OUTPUT_PATH
)