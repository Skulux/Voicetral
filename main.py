import configparser
import ollama
import speech_recognition as sr
from gradio_client import Client
from pydub import AudioSegment
import sounddevice as sd
from scipy.io import wavfile
from short_term_memory import load_conversation_history, save_conversation_history
import logging

# Initialize logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

# Load configuration
config = configparser.ConfigParser()
config.read('config.ini')

# Access configuration values
START_PROMPT = config['DEFAULT']['start_prompt']
OLLAMA_MODEL = config['DEFAULT']['ollama_model']
APPLIO_TTS_VOICE = config['DEFAULT']['applio_tts_voice']
APPLIO_PTH_PATH = config['DEFAULT']['applio_pth_path']
APPLIO_INDEX_PATH = config['DEFAULT']['applio_index_path']
INPUT_DEVICE_INDEX = config.getint('DEFAULT', 'input_device_index')
OUTPUT_DEVICE_INDEX = config.getint('DEFAULT', 'output_device_index')
APPLIO_TTS_OUTPUT_PATH = config['DEFAULT']['applio_tts_output_path']
APPLIO_RVC_OUTPUT_PATH = config['DEFAULT']['applio_rvc_output_path']
FILTERED_CHARS = config['DEFAULT']['filtered_chars']

# Initialize Gradio Client for Applio
client = Client(config['GRADIO_CLIENT']['url'])


def get_ollama_response(prompt, user_id, model=OLLAMA_MODEL, conversation_history=None):
    """
    Get a response from Ollama given a prompt and user ID.
    :param prompt: Your input prompt.
    :param user_id: The ID of the user.
    :param model: The Ollama model to use.
    :param conversation_history: The conversation history dictionary.
    :return: The response from Ollama.
    """
    try:
        # Initialize user conversation history if not already present
        if user_id not in conversation_history:
            conversation_history[user_id] = []

        conversation_history[user_id].append({'role': 'user', 'content': START_PROMPT + prompt})
        ollama_response = ollama.chat(model=model, stream=True, messages=conversation_history[user_id])

        response_content = ""
        for chunk in ollama_response:
            response_content += chunk['message']['content']

        conversation_history[user_id].append({'role': 'assistant', 'content': response_content})
        return response_content
    except Exception as e:
        logging.error(f"An error occurred while getting a response from Ollama: {e}")
        return "[ERROR] Failed to get response."


def convert_text_to_speech(text, output_tts_path, output_rvc_path):
    """
    Convert text to speech using Applio's TTS API.
    :param text: The text to convert to speech.
    :param output_tts_path: The path to save the TTS audio file.
    :param output_rvc_path: The path to save the RVC audio file.
    :return: The path to the RVC audio file.
    """
    try:
        response = client.predict(
            tts_text=text,
            tts_voice=APPLIO_TTS_VOICE,
            output_tts_path=output_tts_path,
            output_rvc_path=output_rvc_path,
            api_name="/run_tts_script"
        )
        logging.info(f"Applio Response: {response}")
        return output_rvc_path
    except Exception as e:
        logging.error(f"Could not convert text to speech: {e}")
        return None


def resample_audio(file_path, target_sample_rate=44100):
    """
    Resample an audio file to a target sample rate.
    :param file_path: File path of the audio file to resample.
    :param target_sample_rate: The target sample rate.
    :return: The path to the resampled audio file.
    """
    try:
        audio = AudioSegment.from_file(file_path)
        audio = audio.set_frame_rate(target_sample_rate)
        resampled_path = file_path.replace(".wav", "_resampled.wav")
        audio.export(resampled_path, format="wav")
        return resampled_path
    except Exception as e:
        logging.error(f"Could not resample audio: {e}")
        return None


def play_audio(file_path, output_device=None):
    """
    Play an audio file using the sounddevice library.
    :param file_path: File path of the audio file to play.
    :param output_device: The output device index to use.
    :return: None
    """
    try:
        sample_rate, audio_data = wavfile.read(file_path)
        sd.play(audio_data, samplerate=sample_rate, device=output_device)
        sd.wait()
    except Exception as e:
        logging.error(f"Could not play audio: {e}")


def speech_to_text(input_device=INPUT_DEVICE_INDEX):
    """
    Convert speech to text using the SpeechRecognition library.
    :param input_device: The input device index to use.
    :return: The recognized text or None if not recognized.
    """
    recognizer = sr.Recognizer()
    with sr.Microphone(device_index=input_device) as source:
        logging.info("Listening...")
        audio = recognizer.listen(source)
        try:
            text = recognizer.recognize_google(audio)
            logging.info(f"You said: {text}")
            return text
        except sr.UnknownValueError:
            logging.error("Could not understand the audio.")
            return None
        except sr.RequestError:
            logging.error("Speech recognition service request failed.")
            return None


def filter_response(input_text, filtered_chars=FILTERED_CHARS):
    """
    Filter out unwanted characters from the input text.
    :param input_text: Input text to filter.
    :param filtered_chars: Characters to filter out.
    :return: Filtered text.
    """
    filtered_text = ''.join(
        char for char in input_text if char.isalnum() or char in filtered_chars)
    if filtered_text != input_text:
        removed_chars = ''.join(char for char in input_text if char not in filtered_text)
        logging.info(f"Removed characters: {removed_chars}")
    return filtered_text


def main():
    """
    Main function to run the combined Ollama and Applio chatbot.
    :return: None
    """
    user_id = "user"
    conversation_history = load_conversation_history(user_id)
    logging.info("Welcome to the combined Ollama and Applio Chatbot!")

    while True:
        user_input = speech_to_text(INPUT_DEVICE_INDEX)
        if user_input:
            if user_input.lower() == "exit":
                save_conversation_history(user_id, conversation_history)
                break

            response = get_ollama_response(user_input, user_id, conversation_history=conversation_history)
            response = filter_response(response)

            tts_path = APPLIO_TTS_OUTPUT_PATH
            rvc_path = APPLIO_RVC_OUTPUT_PATH
            audio_file = convert_text_to_speech(response, tts_path, rvc_path)

            if audio_file:
                resampled_audio = resample_audio(audio_file)
                if resampled_audio:
                    play_audio(resampled_audio, output_device=OUTPUT_DEVICE_INDEX)


if __name__ == "__main__":
    main()
