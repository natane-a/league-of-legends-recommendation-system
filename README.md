# League of Legends Recommendation System

## Overview
The League of Legends Recommendation System is designed to assist players in making optimal decisions on item and rune builds for any champion matchup. This system uses machine learning to provide recommendations based on past successful gameplay data, allowing players to gain a strategic advantage by leveraging historical insights.

## Purpose of the Project
The purpose of this project is to provide League of Legends players with data-driven insights to optimize their champion builds in different matchups. By using real match data and an advanced machine learning model, the system recommends items and runes that have historically yielded high win rates for specific champion matchups. This provides players with guidance that adapts to the evolving meta of League of Legends.

## Detailed Process

### 1. Data Collection
Data collection is done using the Riot Games API to fetch detailed match data. Two endpoints are primarily used:
- `/lol/summoner/v4/summoners/by-name/{summonerName}` - Retrieves the unique PUUID for summoners.
- `/lol/match/v5/matches/by-puuid/{puuid}/ids` - Fetches a list of match IDs.
- `/lol/match/v5/matches/{match_id}` - Retrieves detailed data for each match.

The match history is collected for specific PUUIDs, allowing for large-scale data acquisition covering various champions, positions, and matchups.

### 2. Data Preprocessing and Cleaning
The preprocessing is done using `02_data_preprocessing.ipynb`, where:
- Missing values are filled, such as purchase times for items that were initially missing.
- Data transformation is carried out to normalize numerical features like `goldEarned`, `kills`, `deaths`, etc.
- Special focus is on correctly categorizing item purchases, identifying important items such as legendary items and boots.

The preprocessed data is saved in a suitable format for training the model, ensuring all features are well-prepared.

### 3. Exploratory Data Analysis (EDA)
`03_eda_and_pipeline.ipynb` was used to understand relationships between variables, such as:
- The impact of `kills`, `deaths`, and `assists` on win rates.
- Correlation between different numerical features, such as `goldEarned` and `totalDamageDealt`.
- Using visualization techniques like correlation heatmaps and scatter plots, the dataset was analyzed to ensure meaningful patterns could be extracted.

### 4. Modeling
The recommendation system uses a **RandomForest MultiOutputClassifier** to predict the optimal items and runes:
- **Input Features**: Champion matchups, `kills`, `deaths`, `assists`, `goldEarned`, `win`, etc.
- **Target Features**: `Boots_id`, `Legendary_1_id`, `Legendary_2_id`, and runes (`Keystone`, `PrimarySlot1`, etc.).

The `04_modeling.ipynb` notebook was used for training the model. Hyperparameter tuning was conducted using a randomized search strategy, and the model was stored using `joblib` for future use.

### 5. Challenges Encountered
- **API Rate Limits**: The Riot API has strict rate limits, which required careful handling to avoid hitting request limits. Scripts were designed with retry mechanisms and delays to comply with Riot's restrictions.
- **Data Quality Issues**: Some matches lacked complete information, particularly with item purchase timestamps. A strategy for imputing these values was devised based on item costs and logical assumptions.
- **Model Size**: The trained model reached a size of over 17GB, leading to challenges when trying to use it in production. Reducing model complexity and optimizing memory usage was necessary to make it feasible.

### 6. Deployment
The recommendation system is deployed using two interfaces:
- **Command Line Chatbot**: Implemented in `src/chatbot.py`, this interface allows players to get recommendations directly in the terminal.
- **Streamlit Web Application**: The web app (`src/app.py`) provides an intuitive interface for players, allowing them to input their champion and an opponent to receive recommended item builds and runes.

To run the system:
- **Chatbot**:
  ```bash
  python src/chatbot.py