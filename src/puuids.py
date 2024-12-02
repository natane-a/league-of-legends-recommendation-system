import os
import json
import requests
import time
import datetime
import asyncio
import aiohttp

def load_api_key():
    """
    Load the API key from the credentials file.
    """
    with open("../config/credentials.json", 'r') as f:
        data = json.load(f)
    return data["riot_api_key"]

API_KEY = load_api_key()  # lod API key initially

async def fetch_puuid(session, url, headers, summoner_id):
    """
    Asynchronously fetch the PUUID for a given summoner ID.
    """
    try:
        async with session.get(url, headers=headers) as response:
            print(f"Requesting PUUID for summonerId {summoner_id}, Status: {response.status}")  # Log the response status
            if response.status == 403:  # Forbidden, possible expired API key
                raise Exception("API Key might be expired. Please renew your key.")
            response.raise_for_status()
            summoner_data = await response.json()
            return summoner_data.get("puuid")
    except Exception as e:
        print(f"Error fetching PUUID for summonerId {summoner_id}: {e}")
        return None

async def fetch_puuids(api_key, summoner_ids_path, region, output_path):
    """
    Fetch PUUIDs for summoners given their summoner IDs asynchronously.

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

    # combine all summoner IDs from different branches into a single list
    summoner_ids = []
    for rank in summoner_data:
        summoner_ids.extend(summoner_data[rank])

    headers = {"X-Riot-Token": api_key}
    puuids = []

    # load existing PUUIDs if the output file exists
    if os.path.exists(output_path):
        with open(output_path, 'r') as f:
            existing_puuids = json.load(f)
    else:
        existing_puuids = {}

    # get the list of already processed summoner IDs
    processed_summoner_ids = set(existing_puuids.keys())

    # filter out summoner IDs that have already been processed
    summoner_ids_to_process = [summoner_id for summoner_id in summoner_ids if summoner_id not in processed_summoner_ids]

    request_count = 0
    start_time = datetime.datetime.now()

    async with aiohttp.ClientSession() as session:
        for summoner_id in summoner_ids_to_process:
            current_time = datetime.datetime.now()
            elapsed_seconds = (current_time - start_time).total_seconds()

            if elapsed_seconds > 120:
                # reset the request count after 2 minutes
                request_count = 0
                start_time = current_time

                # update JSON file with the collected PUUIDs so far
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, 'w') as f:
                    json.dump(existing_puuids, f, indent=4)
                print(f"PUUIDs updated and saved to {output_path} after 2-minute interval.")

            if request_count >= 90:
                sleep_time = 120 - elapsed_seconds
                print(f"Approaching 2-minute rate limit. Waiting for {sleep_time:.2f} seconds...")
                await asyncio.sleep(sleep_time)
                request_count = 0
                start_time = datetime.datetime.now()

                # update JSON file with the collected PUUIDs so far
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, 'w') as f:
                    json.dump(existing_puuids, f, indent=4)
                print(f"PUUIDs updated and saved to {output_path} after 2-minute rate limit wait.")

            url = f"https://{region}.api.riotgames.com/lol/summoner/v4/summoners/{summoner_id}"
            puuid = await fetch_puuid(session, url, headers, summoner_id)
            if puuid and puuid not in existing_puuids:
                existing_puuids[summoner_id] = puuid
                # save the updated list immediately after adding a new PUUID
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, 'w') as f:
                    json.dump(existing_puuids, f, indent=4)
                print(f"PUUID for summonerId {summoner_id} saved.")

            request_count += 1

            if request_count % 20 == 0:
                print("20 requests made in the last second. Pausing for 1 second to avoid limit...")
                await asyncio.sleep(1)

    # ensure the output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # save updated PUUIDs to JSON file
    with open(output_path, 'w') as f:
        json.dump(existing_puuids, f, indent=4)

    print(f"PUUIDs updated and saved to {output_path}")
    return list(existing_puuids.values())

# usage
API_KEY = load_api_key()
SUMMONER_IDS_PATH = "../data/raw/summoner_id/summoner_id.json"
REGION = "na1"
OUTPUT_PATH = "../data/raw/puuids/puuids.json"

# run the asynchronous function
asyncio.run(fetch_puuids(
    api_key=API_KEY, 
    summoner_ids_path=SUMMONER_IDS_PATH, 
    region=REGION, 
    output_path=OUTPUT_PATH
))
