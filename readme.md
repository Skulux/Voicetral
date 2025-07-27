# Voicetral

## Overview

This project provides an interface between the Ollama model and a text-to-speech (TTS) engine using gTTS. It converts user speech input into text, generates responses using Ollama, and then synthesizes and plays back the response using gTTS.

## Features

- Speech-to-text conversion using `speech_recognition`.
- Text generation using the Ollama model.
- Text-to-speech conversion using gTTS.
- Audio playback using `sounddevice`.
- Audio resampling and processing with `pydub`.

## Requirements

### Software Dependencies

- Python 3.9
- [FFmpeg](https://ffmpeg.org/download.html) (for audio processing)
- **Ollama**: A model service for text generation. [Visit Ollama's website](https://ollama.com) for installation and usage instructions.
- **gTTS**: Used for text-to-speech synthesis.

### Python Packages

The required Python packages are listed in `requirements.txt`. To install them, use the following command:

    pip install -r requirements.txt

### Configuration

1. **FFmpeg**: Ensure that FFmpeg is installed and accessible in your system's PATH. You can download FFmpeg from [here](https://ffmpeg.org/download.html) and follow the installation instructions for your operating system.

2. **Ollama**: Install and run the Ollama service according to the instructions on their website. Make sure it's accessible at the specified URL.

3. **gTTS**: No additional setup is required for gTTS beyond installing the package.

4. **Configuration File**: Update the `config.ini` file with the appropriate paths and settings for your environment. 

   - `START_PROMPT`: Your initial prompt for the Ollama model.
   - `OLLAMA_MODEL`: The name of the Ollama model to use.
   - `TTS_LANGUAGE`: Language code used by gTTS.
   - `TTS_OUTPUT_PATH`: Path where the TTS output will be saved.

## Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/Skulux/Voicetral
    cd Voicetral
    ```

2. Create and activate a virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. Install the required packages:
    ```bash
    pip install -r requirements.txt
   ```

4. Ensure FFmpeg is installed and properly configured in your PATH.

5. Install and start the Ollama service as per its instructions.

## Usage

1. Configure your `config.ini` file with the necessary settings as described in the Configuration section.

2. Run the main script:
    ```bash
    python main.py
    ```

3. Follow the on-screen prompts. Speak into your microphone to interact with the bot.

4. Say "exit" to stop the program. It is important if you want to save your conversation history.
## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Feel free to submit issues or pull requests if you have suggestions or improvements. For significant changes, please open an issue first to discuss what you would like to change.

## Contact

For questions or feedback, please contact github@petrilionis.lt or open an issue on the project's GitHub repository.

## External Services

- **Ollama**: [Installation and usage instructions](https://ollama.com)
