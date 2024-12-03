# System Architecture Documentation

## Overview
The League of Legends Recommendation System is built using a modular approach to facilitate easy data collection, cleaning, modeling, and recommendation delivery. The system consists of multiple components, each playing a distinct role in the pipeline.

### Components

1. **Data Collection**
   - The data collection process begins with gathering match IDs using Riot API endpoints for a summoner’s ID, PUUID, and match history.
   - Two Riot API endpoints are used:
     - `/lol/summoner/v4/summoners/by-name/{summonerName}` - Retrieves summoner ID.
     - `/lol/match/v5/matches/by-puuid/{puuid}/ids` - Retrieves match IDs.
     - `/lol/match/v5/matches/{match_id}` - Fetches detailed match data.

2. **Data Cleaning and Preprocessing**
   - Data cleaning notebooks (`data_cleaning.ipynb`) remove missing values, incorrect timestamps, and handle items and runes appropriately.
   - Major item upgrades and boots are identified, focusing on important purchases that influence gameplay.

3. **Modeling**
   - The model used is a **RandomForest MultiOutputClassifier** that makes recommendations for item builds and rune setups.
   - The input features consist of champion matchup details, kills, deaths, assists, gold earned, etc., while the target features are the recommended items and runes.

4. **Recommendation Chatbot**
   - A `Streamlit` application serves as the main user interface where users input their champion and the opposing champion, receiving an optimal build.
   - The chatbot is backed by a pre-trained model pickled using `joblib` and loaded during the application startup.

5. **Storage and File Structure**
   - Data is organized into folders:
     - `data/raw/` stores raw JSON match details.
     - `data/processed/` stores processed data.
     - `models/` contains the pickled models.
     - `src/` folder holds the code scripts, including the chatbot and data retrieval scripts.

### Technologies Used
- **Programming Languages**: Python
- **Libraries**: Scikit-learn, Pandas, Requests, Joblib, JSON, Streamlit, Numpy
- **API Integration**: Riot Games API