import discord
from discord.ext import commands
import joblib
import pandas as pd
import json
import asyncio

with open("../config/credentials.json", "r") as f:
    credentials = json.load(f)

DISCORD_BOT_TOKEN = credentials["discord_bot_token"]

# Load data and models
df_path = "../data/processed/transformed_data.csv"  
df = pd.read_csv(df_path)

model_path = "../models/best_recommendation_model.pkl"
best_model = joblib.load(model_path)

pipeline_path = "../models/preprocessing_pipeline.pkl"
pipeline = joblib.load(pipeline_path)

label_encoders_path = "../models/label_encoders.pkl"
label_encoders = joblib.load(label_encoders_path)

with open("../data/raw/champion_data/champions.json", "r") as f:
    champion_data = json.load(f)["data"]

with open("../data/raw/item_data/items.json", "r") as f:
    item_data = json.load(f)["data"]

with open("../data/raw/runes_data/runes.json", "r") as f:
    rune_data = json.load(f)

champion_name_to_id = {v["name"].lower(): int(v["key"]) for k, v in champion_data.items()}
champion_id_to_name = {int(v["key"]): v["name"] for k, v in champion_data.items()}
item_id_to_name = {int(k): v["name"] for k, v in item_data.items()}

rune_id_to_name = {}
rune_id_to_tree = {}
rune_id_to_row = {}
rune_trees = []

for style in rune_data:
    rune_id_to_name[style["id"]] = style["name"]
    rune_trees.append(style["id"])
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

# Prediction function
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
    
    # Ensure unique legendary items
    if predicted_decoded_df['Legendary_1_id'][0] == predicted_decoded_df['Legendary_2_id'][0]:
        current_item = predicted_decoded_df['Legendary_1_id'][0]
        # Find the next best performing item from historical data
        alternative_items = (
            df[(df['championId'] == champion_id) & (df['matchupChampion'] == matchup_champion_id)]['Legendary_2_id']
            .value_counts()
            .index.tolist()
        )
        # Select the first alternative item that is not the current item
        for alt_item in alternative_items:
            if alt_item != current_item:
                predicted_decoded_df["Legendary_2_id"] = alt_item
                break

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

    # If secondary tree matches primary tree, find an alternative tree
    if secondary_tree == primary_tree:
        secondary_tree_options = [t for t in rune_trees if t != primary_tree]
        if secondary_tree_options:
            secondary_tree = secondary_tree_options[0]

    # Replace SecondarySlot1 if it doesn't match the chosen secondary tree
    secondary_tree_options = [t for t in rune_trees if t != primary_tree]

    valid_runes_secondary_1 = df[
        (df['championId'] == champion_id) &
        (df['matchupChampion'] == matchup_champion_id) &
        (df['SecondarySlot1'].apply(lambda x: rune_id_to_tree.get(x, None)).isin(secondary_tree_options))
    ]['SecondarySlot1'].value_counts().index.tolist()

    if valid_runes_secondary_1:
        predicted_decoded_df['SecondarySlot1'] = valid_runes_secondary_1[0]
    else:
        # Fallback: Select any rune from a tree not equal to the primary tree
        all_valid_secondary_1_runes = [
            r for r, t in rune_id_to_tree.items()
            if t != primary_tree
        ]
        if all_valid_secondary_1_runes:
            predicted_decoded_df['SecondarySlot1'] = all_valid_secondary_1_runes[0]

    # Ensure SecondarySlot2 is from the same tree as SecondarySlot1, but not from the same row
    secondary_tree = rune_id_to_tree.get(predicted_decoded_df['SecondarySlot1'][0], None)

    valid_runes_secondary_2 = df[
        (df['championId'] == champion_id) &
        (df['matchupChampion'] == matchup_champion_id) &
        (df['SecondarySlot1'] == predicted_decoded_df['SecondarySlot1'][0]) &
        (df['SecondarySlot2'].apply(lambda x: rune_id_to_tree.get(x, None)) == secondary_tree) &
        (df['SecondarySlot2'].apply(lambda x: rune_id_to_row.get(x, None)) != rune_id_to_row.get(predicted_decoded_df['SecondarySlot1'][0], None))
    ]['SecondarySlot2'].value_counts().index.tolist()

    if valid_runes_secondary_2:
        predicted_decoded_df['SecondarySlot2'] = valid_runes_secondary_2[0]
    else:
        # If no valid rune exists, choose from the secondary tree but ensure no row conflicts
        all_valid_secondary_2_runes = [
            r for r, t in rune_id_to_tree.items()
            if t == secondary_tree and 
            rune_id_to_row.get(r, None) != rune_id_to_row.get(predicted_decoded_df['SecondarySlot1'][0], None)
        ]
        if all_valid_secondary_2_runes:
            predicted_decoded_df['SecondarySlot2'] = all_valid_secondary_2_runes[0]

    def handle_unknown_boots(boots):
        if boots == "Unknown Item":
            return "Plated Steelcaps / Mercury's Treads / Ionian Boots of Lucidity"
        return boots    
                
    # Convert IDs to item and rune names for user-friendly output
    for col in ['Boots_id', 'Legendary_1_id', 'Legendary_2_id']:
        predicted_decoded_df[col] = predicted_decoded_df[col].apply(lambda x: item_id_to_name.get(int(x), "Unknown Item"))
        if col == 'Boots_id':
            predicted_decoded_df[col] = predicted_decoded_df[col].apply(handle_unknown_boots)

    for col in ['Keystone', 'PrimarySlot1', 'PrimarySlot2', 'PrimarySlot3', 'SecondarySlot1', 'SecondarySlot2']:
        predicted_decoded_df[col] = predicted_decoded_df[col].apply(lambda x: rune_id_to_name.get(int(x), "Unknown Rune"))

    return predicted_decoded_df

# Discord Bot Setup
intents = discord.Intents.default()
intents.message_content = True  # Enable message content intent
bot = commands.Bot(command_prefix="!", intents=intents)

# Event: Bot ready
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

# Log received messages and process commands
@bot.event
async def on_message(message):
    if message.author.bot:
        return  # Ignore bot messages
    print(f"Message received: {message.content}")
    await bot.process_commands(message)

# Simple ping command for testing
@bot.command()
async def ping(ctx):
    print("Ping command triggered!")  # Debug log
    await ctx.send("Pong!")

# Recommend command using predict_optimal_build
@bot.command()
async def recommend(ctx, champion: str, opponent: str):
    print(f"Received command: recommend {champion} vs {opponent}")  # Debug log
    try:
        recommended_build = predict_optimal_build(champion, opponent, df, pipeline, best_model, label_encoders)
        response = f"**Recommended Items and Runes for {champion} vs {opponent}:**\n"
        response += "Items:\n"
        response += f"- Boots: {recommended_build['Boots_id'].values[0]}\n"
        response += f"- Legendary Item 1: {recommended_build['Legendary_1_id'].values[0]}\n"
        response += f"- Legendary Item 2: {recommended_build['Legendary_2_id'].values[0]}\n\n"
        response += "Runes:\n"
        response += f"- Keystone: {recommended_build['Keystone'].values[0]}\n"
        response += f"- Primary Slot 1: {recommended_build['PrimarySlot1'].values[0]}\n"
        response += f"- Primary Slot 2: {recommended_build['PrimarySlot2'].values[0]}\n"
        response += f"- Primary Slot 3: {recommended_build['PrimarySlot3'].values[0]}\n"
        response += f"- Secondary Slot 1: {recommended_build['SecondarySlot1'].values[0]}\n"
        response += f"- Secondary Slot 2: {recommended_build['SecondarySlot2'].values[0]}\n"
        print("Sending response...")  # Debug log
        await ctx.send(response)
    except ValueError as e:
        print(f"Error: {str(e)}")  # Debug log
        await ctx.send(f"Error: {str(e)}")
    except Exception as e:
        print(f"An error occurred: {str(e)}")  # Debug log
        await ctx.send(f"An error occurred: {str(e)}")

# Run the bot with proper loop handling
if __name__ == "__main__":
    print("Starting bot...")  # Debug
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(bot.start(DISCORD_BOT_TOKEN))
    finally:
        loop.close()