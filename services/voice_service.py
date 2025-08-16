# Voice Command Integration Service



import whisper
import os

class VoiceService:
    def __init__(self, model_name="base"):
        """
        model_name: Whisper model size (tiny, base, small, medium, large)
        """
        self.model = whisper.load_model(model_name)

    def process_voice(self, audio_path):
        """
        Processes a voice command from an audio file using OpenAI Whisper.
        Args:
            audio_path (str): Path to the audio file (WAV/MP3/FLAC/LINEAR16 recommended)
        Returns:
            str: Transcribed text from audio
        """
        try:
            if not os.path.exists(audio_path):
                return f"Audio file not found: {audio_path}"
            result = self.model.transcribe(audio_path)
            transcript = result.get("text", "")
            return transcript if transcript else "No speech detected."
        except Exception as e:
            return f"Voice processing error: {e}"
