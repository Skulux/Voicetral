import configparser
import ollama
import speech_recognition as sr
import whisper
from gradio_client import Client
from pydub import AudioSegment
import sounddevice as sd
from scipy.io import wavfile
from short_term_memory import load_conversation_history, save_conversation_history
import logging
import time
import wave
import tempfile
import numpy as np


# Initialize logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
model = whisper.load_model("base")

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


def time_wrapper(func):
    """
    Wrapper function to measure the time taken by a function.
    :param func: The function to measure.
    :return: The wrapped function.
    """
    def wrapper(*args, **kwargs):
        logging.info(f"Running {func.__name__}...")
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        logging.info(f"{func.__name__} took {round(end_time - start_time, 2)} seconds")
        return result
    return wrapper


@time_wrapper
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

        # shorten conversation history to last 3 messages + first message
        if len(conversation_history[user_id]) > 3:
            shortened_history = conversation_history[user_id][-3:]
            shortened_history.insert(0, conversation_history[user_id][0])


        # Add user message to conversation history
        conversation_history[user_id].append({'role': 'user', 'content': START_PROMPT + prompt})

        # Get the response from Ollama without streaming
        ollama_response = ollama.chat(model=model, stream=False, messages=conversation_history[user_id])

        # Directly extract the response content
        response_content = ollama_response['message']['content']

        # Add assistant's response to conversation history
        conversation_history[user_id].append({'role': 'assistant', 'content': response_content})

        return response_content
    except Exception as e:
        logging.error(f"[OLLAMA] An error occurred while getting a response from Ollama: {e}")
        return "[ERROR] Failed to get response."


@time_wrapper
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
            pth_path=APPLIO_PTH_PATH,
            index_path=APPLIO_INDEX_PATH,
            tts_rate=0,
            pitch=0,
            filter_radius=3,
            index_rate=0.75,
            volume_envelope=1,
            protect=0.5,
            hop_length=128,
            f0_method="rmvpe",
            split_audio=False,
            f0_autotune=False,
            clean_audio=True,
            clean_strength=0.5,
            export_format="WAV",
            upscale_audio=False,
            f0_file=None,
            embedder_model="contentvec",
            embedder_model_custom=None,
            api_name="/run_tts_script"
        )
        logging.info(f"Response: {response}")
        return output_rvc_path
    except Exception as e:
        logging.error(f"Could not convert text to speech: {e}")
        return None


@time_wrapper
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
        try:
            resampled_path = file_path.replace(".wav", "_resampled.wav")
            audio.export(resampled_path, format="wav")
        except IOError as e:
            logging.error(f"Error exporting resampled audio: {e}")
            logging.info("Exporting to default path: non_resampled.wav")
            audio.export("non_resampled.wav", format="wav")
            return "non_resampled.wav"
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


def speech_to_text_whisper(audio_file):
    """
    Convert speech to text using the Whisper model.
    :param audio_file: The path to the audio file to transcribe.
    :return: The recognized text or None if not recognized.
    """
    try:
        logging.info("Transcribing audio using Whisper...")
        result = model.transcribe(audio_file)  # Pass the path of the audio file
        text = result['text']
        logging.info(f"Transcribed text: {text}")
        return text
    except Exception as e:
        logging.error(f"Whisper transcription failed: {e}")
        return None


@time_wrapper
def speech_to_text(input_device=INPUT_DEVICE_INDEX, mode="sr"):
    """
    Convert speech to text using either the SpeechRecognition library or Whisper.
    :param input_device: The input device index to use.
    :param mode: The mode of transcription ('sr' for SpeechRecognition or 'whisper' for Whisper).
    :return: The recognized text or None if not recognized.
    """
    recognizer = sr.Recognizer()

    with sr.Microphone(device_index=input_device) as source:
        logging.info("Listening...")
        audio = recognizer.listen(source)
        logging.info("Audio captured.")

        try:
            if mode == "sr":
                # Using SpeechRecognition
                text = recognizer.recognize_google(audio)
                logging.info(f"You said: {text}")
                return text
            elif mode == "whisper":
                # Save the audio to a temporary file for Whisper
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                    temp_file_name = temp_file.name
                    # Save audio data
                    with wave.open(temp_file_name, 'wb') as wf:
                        wf.setnchannels(1)  # Mono
                        wf.setsampwidth(2)  # Sample width in bytes
                        wf.setframerate(44100)  # Sample rate
                        wf.writeframes(audio.get_raw_data())  # Write audio data

                # Call the Whisper transcription function
                return speech_to_text_whisper(temp_file_name)
            else:
                logging.error(f"Invalid mode specified: {mode}")
                return None
        except sr.UnknownValueError:
            logging.error("Could not understand the audio.")
            return None
        except sr.RequestError:
            logging.error("Speech recognition service request failed.")
            return None
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")
            return None


@time_wrapper
def speech_to_text(input_device=INPUT_DEVICE_INDEX, mode="sr"):
    """
    Convert speech to text using either the SpeechRecognition library or Whisper.
    :param input_device: The input device index to use.
    :param mode: The mode of transcription ('sr' for SpeechRecognition or 'whisper' for Whisper).
    :return: The recognized text or None if not recognized.
    """
    recognizer = sr.Recognizer()

    with sr.Microphone(device_index=input_device) as source:
        logging.info("Listening...")
        audio = recognizer.listen(source)
        logging.info("Audio captured.")

        try:
            if mode == "sr":
                # Using SpeechRecognition
                text = recognizer.recognize_google(audio)
                logging.info(f"You said: {text}")
                return text
            elif mode == "whisper":
                # Save the audio to a temporary file for Whisper
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                    temp_file_name = temp_file.name
                    # Save audio data
                    with wave.open(temp_file_name, 'wb') as wf:
                        wf.setnchannels(1)  # Mono
                        wf.setsampwidth(2)  # Sample width in bytes
                        wf.setframerate(44100)  # Sample rate
                        wf.writeframes(audio.get_raw_data())  # Write audio data

                # Call the Whisper transcription function
                return speech_to_text_whisper(temp_file_name)
            else:
                logging.error(f"Invalid mode specified: {mode}")
                return None
        except sr.UnknownValueError:
            logging.error("Could not understand the audio.")
            return None
        except sr.RequestError:
            logging.error("Speech recognition service request failed.")
            return None
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")
            return None

@time_wrapper
def filter_response(input_text, filtered_chars=FILTERED_CHARS):
    """
    Filter out unwanted characters from the input text.
    :param input_text: Input text to filter.
    :param filtered_chars: Characters to filter out.
    :return: Filtered text.
    """
    sym = [' ', '?', '!', '.', ',', ':', ';', '-', "'", '*']
    filtered_text = ''.join(
        char for char in input_text if (char.isalnum() or char in sym) and char not in filtered_chars)
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
    logging.info("Welcome to the Voicetral!\nTalk to me or say 'exit' to end and save the conversation")

    while True:
        user_input = speech_to_text(input_device=INPUT_DEVICE_INDEX, mode="whisper")
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
