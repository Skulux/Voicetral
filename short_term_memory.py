import json
import logging
import os

def save_conversation_history(user_id, conversation_history):
    """
    Saves the conversation history to a JSON file.

    :param user_id: The ID of the user whose conversation history is being saved.
    :param conversation_history: The conversation history dictionary.
    """
    temp_path = f"conversation_history_{user_id}.json.temp"
    try:
        with open(temp_path, "w") as file:
            json.dump(conversation_history, file)
        os.replace(temp_path, f"conversation_history_{user_id}.json")
    except Exception as e:
        logging.error(f"Error saving conversation history: {e}")

def load_conversation_history(user_id):
    """
    Loads the conversation history from a JSON file.

    :param user_id: The ID of the user whose conversation history is being loaded.
    :return: The loaded conversation history or an empty dictionary if not found.
    """
    try:
        with open(f"conversation_history_{user_id}.json", "r") as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"No previous conversation history found for user: {user_id}. Starting new conversation.")
        return {}
    except Exception as e:
        print(f"Error loading conversation history: {e}")
        return {}
