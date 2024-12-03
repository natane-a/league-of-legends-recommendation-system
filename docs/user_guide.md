# User Guide: League of Legends Recommendation System

## Overview
This user guide provides instructions for using the League of Legends recommendation system, which includes a chatbot and a web app to provide optimal item and rune builds for any given champion matchup. Below are detailed steps for setting up, running, and understanding the various components of the system.

## Setting Up
- Make sure you have cloned the project repository and have installed the required dependencies. You can install the dependencies using:
  ```bash
  pip install -r requirements.txt
  ```
## Configuration

Ensure you have a Riot Games API key. Save it in the following format in the `config` folder:

### File: `config/credentials.json`

```json
{
  "riot_api_key": "YOUR_API_KEY_HERE"
}
```

## Using the Chatbot

The chatbot allows you to interactively get recommendations by providing your champion and the opponent’s champion.

### Launch the Chatbot

To start the chatbot, run the following command:

```bash
python src/chatbot.py
```

### Provide Champion Names

- **Enter your champion's name**.
- **Enter the opponent champion's name**.

### Get Recommendations

The chatbot will return an optimal item and rune setup based on historical data and previous successful match builds.

### Exit the Chatbot

Type `"exit"` at any point to close the chatbot.

## Using the Web Application

The system also provides a user-friendly web interface using **Streamlit**.

### Run the Web App

To start the web application, run the following command:

```bash
streamlit run src/app.py
```

### Provide Input

- **Input the name of your champion**.
- **Input the opponent’s champion**.

### Get Recommendations

The app will display the best possible item and rune builds for your input.

## Retraining the Model

If you want to update the recommendations based on new data, follow these steps:

### 1. Collect New Match Data

- **Run the data collection scripts** located in the `src/` folder.
  - Use the script `match_history.py` to collect new match IDs.
  - Use `match_details.py` to retrieve match details.

Make sure you have a valid Riot API key and adjust the scripts accordingly.

### 2. Data Cleaning

- Run the notebook `02_data_cleaning.ipynb` to clean and preprocess the newly collected match details.

### 3. Model Training

- Use `04_modeling.ipynb` to retrain the model based on the cleaned dataset.
- Update the model by saving the new pickle file in the `models/` directory.

### Keeping Recommendations Up-to-Date

The retraining process ensures that your recommendations stay up-to-date with the latest patch notes, item adjustments, and evolving game meta.
```

This is the entire text formatted as a markdown file, which can be saved as `user_guide.md`.