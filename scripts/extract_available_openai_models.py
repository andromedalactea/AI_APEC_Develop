import os
import requests
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv(override=True)

def extract_openai_models() -> list:
    """
    Retrieves a list of OpenAI models that contain 'gpt' in their IDs.

    Returns:
        list: A list of model IDs that include 'gpt'.
    """
    # API URL to fetch the list of models
    url = 'https://api.openai.com/v1/models'

    # Request headers including the authorization token
    headers = {
        'Authorization': f'Bearer {os.getenv("OPENAI_API_KEY")}',
    }

    # Make the GET request to the OpenAI API
    response = requests.get(url, headers=headers)

    # Check if the request was successful
    if response.status_code == 200:
        # Extract the list of models from the response
        list_all_models = list(response.json().get('data', []))
        
        # List to store filtered models
        filter_models = []

        # Iterate over all models to filter those containing 'gpt' in their ID
        for model in list_all_models:
            id_model = model.get('id', '')
            if 'gpt' in id_model:
                # Add model ID to the filtered list if 'gpt' is found
                filter_models.append(id_model + "_APEC")

        # Return the list of filtered model IDs
        return filter_models
    else:
        # If the request failed, return a default model as a fallback
        return ['gpt-4o']

# Example usage
if __name__ == '__main__':
    models = extract_openai_models()
    print(models)
