import streamlit as st
import joblib
import json
import pandas as pd

df_path = '../data/processed/transformed_data.csv'
df = pd.read_csv(df_path)

# Load the model and pipeline
model_path = "../models/best_recommendation_model.pkl"
pipeline_path = "../models/preprocessing_pipeline.pkl"

@st.cache(allow_output_mutation=True)
def load_model():
    return joblib.load("../models/best_recommendation_model.pkl")

best_model = load_model()
pipeline = joblib.load(pipeline_path)

# Load champion, item, and rune datasets
with open("../data/raw/champion_data/champions.json", "r") as f:
    champion_data = json.load(f)["data"]

with open("../data/raw/item_data/items.json", "r") as f:
    item_data = json.load(f)["data"]

with open("../data/raw/runes_data/runes.json", "r") as f:
    rune_data = json.load(f)

# creating lookup dictionaries
champion_name_to_id = {v["name"].lower(): int(v["key"]) for k, v in champion_data.items()}
champion_id_to_name = {int(v["key"]): v["name"] for k, v in champion_data.items()}

item_id_to_name = {int(k): v["name"] for k, v in item_data.items()}

# extract rune IDs and names properly from runes data
rune_id_to_name = {}
for style in rune_data:
    # add the main style name
    rune_id_to_name[style["id"]] = style["name"]

    # add individual runes within each style
    for slot in style["slots"]:
        for rune in slot["runes"]:
            rune_id_to_name[rune["id"]] = rune["name"]


target_features = [
    "Boots_id", "Legendary_1_id", "Legendary_2_id",
    "Keystone", "PrimarySlot1", "PrimarySlot2",
    "PrimarySlot3", "SecondarySlot1", "SecondarySlot2"
]

def predict_optimal_build(champion_name, matchup_champion_name, df, pipeline, model):
    """
    Predict the optimal item build and runes for the given champion and matchup champion.
    
    Parameters:
    - champion_name: str, champion name of the player.
    - matchup_champion_name: str, champion name of the opponent.
    - df: DataFrame, original DataFrame with historical data.
    - pipeline: preprocessing pipeline used for transforming the features.
    - model: trained MultiOutputClassifier model.

    Returns:
    - DataFrame, containing the predicted items and runes.
    """
    # convert champion names to IDs
    champion_id = champion_name_to_id.get(champion_name.lower())
    matchup_champion_id = champion_name_to_id.get(matchup_champion_name.lower())

    if champion_id is None or matchup_champion_id is None:
        raise ValueError(f"Champion name(s) provided are not valid: {champion_name}, {matchup_champion_name}")

    # create a new input dataFrame with average values
    input_data = df[(df['championId'] == champion_id) & (df['matchupChampion'] == matchup_champion_id)].mean().to_dict()

    # check if input_data has null values and provide default values
    if pd.isna(pd.Series(input_data)).any():
        raise ValueError(f"No data available for the matchup: {champion_name} vs {matchup_champion_name}")


    # override champion-specific fields
    input_data['championId'] = champion_id
    input_data['matchupChampion'] = matchup_champion_id

    # create a dataFrame for input
    input_features = df.columns.difference(target_features)
    input_df = pd.DataFrame([input_data], columns=input_features)

    # preprocess the input features using the pipeline
    input_processed = pipeline.transform(input_df)

    # predict the output
    predicted_output = model.predict(input_processed)

    # convert the prediction to a DataFrame for better readability
    predicted_df = pd.DataFrame(predicted_output, columns=target_features)

    # convert IDs to item and rune names for user-friendly output
    for col in ['Boots_id', 'Legendary_1_id', 'Legendary_2_id']:
        predicted_df[col] = predicted_df[col].apply(lambda x: item_id_to_name.get(int(x), "Unknown Item"))

    for col in ['Keystone', 'PrimarySlot1', 'PrimarySlot2', 'PrimarySlot3', 'SecondarySlot1', 'SecondarySlot2']:
        predicted_df[col] = predicted_df[col].apply(lambda x: rune_id_to_name.get(int(x), "Unknown Rune"))

    return predicted_df

# Streamlit UI
st.title("League of Legends Recommendation System")
champion_name = st.text_input("Enter your champion name:")
matchup_champion_name = st.text_input("Enter opponent champion name:")

if st.button("Get Recommendation"):
    if champion_name and matchup_champion_name:
        try:
            recommended_build = predict_optimal_build(champion_name, matchup_champion_name, df, pipeline, best_model)
            st.subheader("Recommended Items and Runes:")
            st.write(f"**Boots**: {recommended_build['Boots_id'].values[0]}")
            st.write(f"**Legendary Item 1**: {recommended_build['Legendary_1_id'].values[0]}")
            st.write(f"**Legendary Item 2**: {recommended_build['Legendary_2_id'].values[0]}")
            st.write(f"**Keystone**: {recommended_build['Keystone'].values[0]}")
            st.write(f"**Primary Slot 1**: {recommended_build['PrimarySlot1'].values[0]}")
            st.write(f"**Primary Slot 2**: {recommended_build['PrimarySlot2'].values[0]}")
            st.write(f"**Primary Slot 3**: {recommended_build['PrimarySlot3'].values[0]}")
            st.write(f"**Secondary Slot 1**: {recommended_build['SecondarySlot1'].values[0]}")
            st.write(f"**Secondary Slot 2**: {recommended_build['SecondarySlot2'].values[0]}")
        except ValueError as e:
            st.error(str(e))
    else:
        st.warning("Please enter both champion and opponent names.")