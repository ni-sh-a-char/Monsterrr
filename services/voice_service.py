# Voice Command Integration Service


from google.cloud import speech
import io

class VoiceService:
    def __init__(self, credentials_path=None):
        """
        credentials_path: Path to Google Cloud credentials JSON file.
        If None, will use default credentials.
        """
        if credentials_path:
            from google.oauth2 import service_account
            credentials = service_account.Credentials.from_service_account_file(credentials_path)
            self.client = speech.SpeechClient(credentials=credentials)
        else:
            self.client = speech.SpeechClient()

    def process_voice(self, audio_path):
        """
        Processes a voice command from an audio file using Google Speech-to-Text.
        Args:
            audio_path (str): Path to the audio file (WAV/FLAC/LINEAR16 recommended)
        Returns:
            str: Transcribed text from audio
        """
        try:
            with io.open(audio_path, "rb") as audio_file:
                content = audio_file.read()
            audio = speech.RecognitionAudio(content=content)
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=16000,
                language_code="en-US",
            )
            response = self.client.recognize(config=config, audio=audio)
            transcript = " ".join([result.alternatives[0].transcript for result in response.results])
            return transcript if transcript else "No speech detected."
        except Exception as e:
            return f"Voice processing error: {str(e)}"
