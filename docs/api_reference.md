# Riot API Reference for Data Collection

## Overview
This recommendation system makes extensive use of the Riot Games API for collecting player and match data. Below are the details of each endpoint used:

### Summoner API
- **Endpoint**: `/lol/summoner/v4/summoners/by-name/{summonerName}`
- **Purpose**: Retrieves information about a summoner, including their unique summoner ID and PUUID.
- **Parameters**:
  - `summonerName`: Name of the summoner.

### PUUID API
- **Endpoint**: `/lol/summoner/v4/summoners/by-puuid/{puuid}`
- **Purpose**: Retrieves summoner information by providing a unique PUUID. This is particularly useful for matching records across multiple APIs.
- **Parameters**:
  - `puuid`: The unique identifier for the summoner provided by Riot.
- **Response**: Includes summoner information such as `summonerName`, `level`, and other player-specific data.


### Match History API
- **Endpoint**: `/lol/match/v5/matches/by-puuid/{puuid}/ids`
- **Purpose**: Fetches a list of match IDs that a player has participated in.
- **Parameters**:
  - `puuid`: Unique identifier for a player.

### Match Details API
- **Endpoint**: `/lol/match/v5/matches/{match_id}`
- **Purpose**: Provides detailed data about a specific match.
- **Parameters**:
  - `match_id`: Unique ID for the match.

### Rate Limiting
- Riot API is rate-limited, allowing:
  - 20 requests per second and 100 requests every 2 minutes globally.
  - Scripts in `src/` handle rate-limiting and retry mechanisms.