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

def fetch_match_ids(api_key, puuid, region, count=10):
    """
    Fetch match IDs for a given PUUID, filtering for ranked solo/duo games only.

    Parameters:
    - api_key: str, Riot Games API key.
    - puuid: str, PUUID of the summoner.
    - region: str, region for match data (e.g., "americas").
    - count: int, number of matches to retrieve.

    Returns:
    - match_ids: list of match IDs.
    """
    headers = {"X-Riot-Token": api_key}
    url = f"https://{region}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?queue=420&start=0&count={count}"
    # queue=420 ensures only ranked solo/duo matches are fetched
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 403:  # possible expired API key
            raise Exception("API Key might be expired. Please renew your key.")
        response.raise_for_status()
        match_ids = response.json()
        return match_ids
    except requests.exceptions.RequestException as e:
        print(f"Error fetching match IDs for PUUID {puuid}: {e}")
        return []

def load_puuids(puuids_path):
    """
    Load PUUIDs from a JSON file.

    Parameters:
    - puuids_path: str, path to the JSON file containing PUUIDs.

    Returns:
    - list of PUUIDs.
    """
    if not os.path.exists(puuids_path):
        print(f"PUUIDs file not found: {puuids_path}")
        return []

    with open(puuids_path, 'r') as f:
        puuids_data = json.load(f)
        return list(puuids_data.values())[::-1] if isinstance(puuids_data, dict) else puuids_data[::-1]

# usage
API_KEY = load_api_key()
PUUIDS_PATH = "../data/raw/puuids/puuids.json"
REGION = "americas"
MATCH_OUTPUT_PATH = "../data/raw/match_ids/match_ids.json"

# load PUUIDs from file
puuids = load_puuids(PUUIDS_PATH)

# fetch match IDs for each PUUID from bottom to top and append to existing JSON
if puuids:
    # ensure the output directory exists
    os.makedirs(os.path.dirname(MATCH_OUTPUT_PATH), exist_ok=True)

    # load existing match IDs to handle duplicates
    if os.path.exists(MATCH_OUTPUT_PATH):
        with open(MATCH_OUTPUT_PATH, 'r') as f:
            existing_match_ids = set(json.load(f))
    else:
        existing_match_ids = set()

    request_count = 0
    start_time = datetime.datetime.now()

    # iterate over PUUIDs from bottom to top
    for puuid in puuids:
        while True:
            try:
                # check request rate limits
                current_time = datetime.datetime.now()
                elapsed_seconds = (current_time - start_time).total_seconds()

                # if 100 requests made in less than 2 minutes, wait until rate limit resets
                if request_count >= 100 and elapsed_seconds < 120:
                    sleep_time = 120 - elapsed_seconds
                    print(f"Approaching 2-minute rate limit. Waiting for {sleep_time:.2f} seconds...")
                    time.sleep(sleep_time)
                    request_count = 0
                    start_time = datetime.datetime.now()

                # if 20 requests made in the last second, wait for the next second
                if request_count % 20 == 0 and request_count > 0:
                    print("20 requests made in the last second. Pausing for 1 second to avoid limit...")
                    time.sleep(1)

                match_ids = fetch_match_ids(API_KEY, puuid, REGION)
                existing_match_ids.update(match_ids)

                # save updated match IDs to JSON file
                with open(MATCH_OUTPUT_PATH, 'w') as f:
                    json.dump(list(existing_match_ids), f, indent=4)

                print(f"Fetched and appended match IDs for PUUID {puuid} to {MATCH_OUTPUT_PATH}")
                request_count += 1
                break

            except Exception as e:
                print(f"Error: {e}")
                if "expired" in str(e).lower():
                    API_KEY = input("API key expired. Please enter a new API key: ")
                else:
                    break
else:
    print("No PUUIDs found in the provided file.")
