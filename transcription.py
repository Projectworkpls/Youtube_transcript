import tempfile
import os
import time
import yt_dlp
import whisper
import torch
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class TranscriptionService:
    def __init__(self):
        self.model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._model_loaded = False

    def load_model(self):
        """Load the Whisper model"""
        if not self._model_loaded:
            torch.cuda.empty_cache() if self.device == "cuda" else None
            self.model = whisper.load_model("small", device=self.device)
            self._model_loaded = True
        return self.model

    def _get_ydl_options(self):
        """Return yt-dlp options with headers and cookies support"""
        return {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(tempfile.gettempdir(), "%(id)s.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
                "Accept-Language": "en-US,en;q=0.5",
            },
            "cookiefile": "cookies.txt" if os.path.exists("cookies.txt") else None,
        }

    def download_audio(self, url):
        """Download audio using yt-dlp"""
        try:
            ydl_opts = self._get_ydl_options()
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return ydl.prepare_filename(info).replace(".webm", ".mp3").replace(".m4a", ".mp3")
        except Exception as e:
            raise ValueError(f"Download failed: {str(e)}")

    def transcribe_audio(self, audio_path):
        """Transcribe audio using Whisper"""
        try:
            model = self.load_model()
            result = model.transcribe(audio_path, fp16=(self.device == "cuda"))
            os.remove(audio_path)
            return result["text"]
        except Exception as e:
            if os.path.exists(audio_path):
                os.remove(audio_path)
            raise ValueError(f"Transcription error: {str(e)}")

    def process_video(self, url):
        """Main processing method"""
        if not url.startswith(('http://', 'https://')):
            url = f'https://{url}'

        parsed = urlparse(url)
        if not any(x in parsed.netloc for x in ['youtube.com', 'youtu.be']):
            raise ValueError("Invalid YouTube URL")

        audio_path = self.download_audio(url)
        return self.transcribe_audio(audio_path)