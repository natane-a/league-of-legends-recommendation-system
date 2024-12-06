import joblib
import pandas as pd
import json

df_path = "../data/processed/transformed_data.csv"  
df = pd.read_csv(df_path)

model_path = "../models/best_recommendation_model.pkl"
try:
    best_model = joblib.load(model_path)
except Exception as e:
    print(f"Error loading model: {e}")

# preprocessing pipeline
pipeline_path = "../models/preprocessing_pipeline.pkl"
pipeline = joblib.load(pipeline_path)

# load label encoders
label_encoders_path = "../models/label_encoders.pkl"
label_encoders = joblib.load(label_encoders_path)

# loading champion, item, and rune datasets
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

# create lookup dictionaries for rune names and rune trees
rune_id_to_name = {}
rune_id_to_tree = {}
rune_id_to_row = {}
rune_trees = []

for style in rune_data:
    # add the main style name
    rune_id_to_name[style["id"]] = style["name"]
    rune_trees.append(style["id"])  # Store available rune trees

    # add individual runes within each style and map each rune to its tree and row
    for row_idx, slot in enumerate(style["slots"]):
        for rune in slot["runes"]:
            rune_id_to_name[rune["id"]] = rune["name"]
            rune_id_to_tree[rune["id"]] = style["id"]
            rune_id_to_row[rune["id"]] = row_idx


target_features = [
    "Boots_id", "Legendary_1_id", "Legendary_2_id",
    "Keystone", "PrimarySlot1", "PrimarySlot2",
    "PrimarySlot3", "SecondarySlot1", "SecondarySlot2"
]

def predict_optimal_build(champion_name, matchup_champion_name, df, pipeline, model, label_encoders):
    """
    Predict the optimal item build and runes for the given champion and matchup champion.
    
    Parameters:
    - champion_name: str, champion name of the player.
    - matchup_champion_name: str, champion name of the opponent.
    - df: DataFrame, original DataFrame with historical data.
    - pipeline: preprocessing pipeline used for transforming the features.
    - model: trained MultiOutputClassifier model.
    - label_encoders: dict, dictionary of LabelEncoders for each target feature.

    Returns:
    - DataFrame, containing the predicted items and runes.
    """
    # Convert champion names to IDs
    champion_id = champion_name_to_id.get(champion_name.lower())
    matchup_champion_id = champion_name_to_id.get(matchup_champion_name.lower())

    if champion_id is None or matchup_champion_id is None:
        raise ValueError(f"Champion name(s) provided are not valid: {champion_name}, {matchup_champion_name}")

    # Create a new input DataFrame with average values for other features
    input_data = df[(df['championId'] == champion_id) & (df['matchupChampion'] == matchup_champion_id)].mean().to_dict()

    # Check if input_data has NaN values and provide default values if needed
    if any(pd.isna(value) for value in input_data.values()):
        raise ValueError(f"No data available for the matchup: {champion_name} vs {matchup_champion_name}")

    # Override champion-specific fields
    input_data['championId'] = champion_id
    input_data['matchupChampion'] = matchup_champion_id

    # Create a DataFrame for input
    input_features = df.columns.difference(target_features)
    input_df = pd.DataFrame([input_data], columns=input_features)

    # Preprocess the input features using the pipeline
    input_processed = pipeline.transform(input_df)

    # Predict the output
    predicted_output = model.predict(input_processed)

    # Convert the prediction to a DataFrame for easier handling
    predicted_encoded_df = pd.DataFrame(predicted_output, columns=target_features)

    # Decode the predictions using the stored LabelEncoders
    predicted_decoded_df = pd.DataFrame()
    for col in target_features:
        predicted_decoded_df[col] = label_encoders[col].inverse_transform(predicted_encoded_df[col])

    # Validate rune selections - ensure they come from the same tree
    primary_tree = rune_id_to_tree.get(predicted_decoded_df['Keystone'][0], None)
    for col in ['PrimarySlot1', 'PrimarySlot2', 'PrimarySlot3']:
        if rune_id_to_tree.get(predicted_decoded_df[col][0]) != primary_tree:
            # Replace with the most frequent rune from the primary tree if it doesn't match
            valid_runes = df[(df['Keystone'] == predicted_decoded_df['Keystone'][0])][col].value_counts().index.tolist()
            if valid_runes:
                predicted_decoded_df[col] = valid_runes[0]

    # Validate that secondary runes come from the correct tree
    secondary_tree = rune_id_to_tree.get(predicted_decoded_df['SecondarySlot1'][0], None)
    if secondary_tree == primary_tree:
        # Ensure secondary tree is different from the primary tree
        secondary_tree_options = [t for t in rune_trees if t != primary_tree]
        secondary_tree = secondary_tree_options[0]  # Replace with the first different tree found

    for col in ['SecondarySlot1', 'SecondarySlot2']:
        if rune_id_to_tree.get(predicted_decoded_df[col][0]) != secondary_tree:
            if col == 'SecondarySlot2':
                # If `SecondarySlot2` doesn't match, find the most frequent rune that pairs well historically
                valid_runes = df[(df['championId'] == champion_id) & 
                                 (df['matchupChampion'] == matchup_champion_id) & 
                                 (df['SecondarySlot1'] == predicted_decoded_df['SecondarySlot1'][0])][col].value_counts().index.tolist()
                if valid_runes:
                    predicted_decoded_df[col] = valid_runes[0]

    # Convert IDs to item and rune names for user-friendly output
    for col in ['Boots_id', 'Legendary_1_id', 'Legendary_2_id']:
        predicted_decoded_df[col] = predicted_decoded_df[col].apply(lambda x: item_id_to_name.get(int(x), "Unknown Item"))

    for col in ['Keystone', 'PrimarySlot1', 'PrimarySlot2', 'PrimarySlot3', 'SecondarySlot1', 'SecondarySlot2']:
        predicted_decoded_df[col] = predicted_decoded_df[col].apply(lambda x: rune_id_to_name.get(int(x), "Unknown Rune"))

    return predicted_decoded_df

def chatbot():
    print("Welcome to the League of Legends Recommendation Chatbot!")
    print("Type 'exit' at any time to quit.")
    while True:
        champion = input("Enter your champion: ").strip().lower()
        opponent = input("Enter the opponent champion: ").strip().lower()

        if champion == "exit" or opponent == "exit":
            print("Goodbye!")
            break

        try:
            # making a prediction
            recommended_build = predict_optimal_build(champion, opponent, df, pipeline, best_model, label_encoders)
            print("\nRecommended Items and Runes for the given matchup:")
            print("Items:")
            print(f"  Boots: {recommended_build['Boots_id'].values[0]}")
            print(f"  Legendary Item 1: {recommended_build['Legendary_1_id'].values[0]}")
            print(f"  Legendary Item 2: {recommended_build['Legendary_2_id'].values[0]}")
            print("\nRunes:")
            print(f"  Keystone: {recommended_build['Keystone'].values[0]}")
            print(f"  Primary Slot 1: {recommended_build['PrimarySlot1'].values[0]}")
            print(f"  Primary Slot 2: {recommended_build['PrimarySlot2'].values[0]}")
            print(f"  Primary Slot 3: {recommended_build['PrimarySlot3'].values[0]}")
            print(f"  Secondary Slot 1: {recommended_build['SecondarySlot1'].values[0]}")
            print(f"  Secondary Slot 2: {recommended_build['SecondarySlot2'].values[0]}")
        except ValueError as e:
            print(f"Error: {e}. Please try again.")

if __name__ == "__main__":
    chatbot()