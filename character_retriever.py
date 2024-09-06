import json
import random

def load_json_from_file(file_path):
    # Open the JSON file and load the data
    with open(file_path, 'r') as file:
        data = json.load(file)
    return data

def get_description_by_category(file_path, category):
    # Load data from the JSON file
    data = load_json_from_file(file_path)
    
    # Initialize an empty list to store descriptions
    descriptions = []
    
    # Iterate through each character in the data
    for character in data['characters']:
        # Check if the input category is in the character's categories
        if category in character['categories']:
            # Append the description to the descriptions list
            descriptions.append(character['description'])
    
    # Return the descriptions list
    return descriptions

if __name__ == "__main__":
    characters = get_description_by_category("tiktok_characters.json", "donaldtrump")
    character = random.choice(characters)

    print("Retrieved character:\n",character)
    
    prompt = f"Generate the text for this tiktok as if you are a {character}, no hashtags, no future tense, max three sentences: [TIKTOK_CONTEXT]"
    print("\n\nPrompt example:\n", prompt)