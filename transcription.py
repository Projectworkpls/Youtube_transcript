import whisper
import torch
import tempfile
import os
import yt_dlp
import random
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class TranscriptionService:
    def __init__(self):
        self.model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15..."
        ]
        self.cookie_file = "cookies.txt" if os.path.exists("cookies.txt") else None

    def load_model(self):
        if not self.model:
            torch.cuda.empty_cache() if self.device == "cuda" else None
            self.model = whisper.load_model("small", device=self.device)
        return self.model

    def _get_ydl_options(self):
        return {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(tempfile.gettempdir(), "%(id)s.%(ext)s"),
            "http_headers": {
                "User-Agent": random.choice(self.user_agents),
                "Accept-Language": "en-US,en;q=0.5",
                "Referer": "https://www.youtube.com/"
            },
            "cookiefile": self.cookie_file,
            "retries": 10,
            "ignoreerrors": True,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }]
        }

    def download_audio(self, url):
        try:
            ydl_opts = self._get_ydl_options()
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                return filename.replace(".webm", ".mp3").replace(".m4a", ".mp3")
        except Exception as e:
            raise ValueError(f"Download failed: {str(e)}")

    def transcribe_audio(self, audio_path):
        try:
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"Audio file not found: {audio_path}")

            self.load_model()
            result = self.model.transcribe(
                audio_path,
                fp16=(self.device == "cuda"),
                language="en"
            )
            os.remove(audio_path)
            return result["text"]
        except Exception as e:
            if os.path.exists(audio_path):
                os.remove(audio_path)
            raise ValueError(f"Transcription error: {str(e)}")

    def process_video(self, url):
        try:
            parsed = urlparse(url)
            if not any(x in parsed.netloc for x in ['youtube.com', 'youtu.be']):
                raise ValueError("Invalid YouTube URL")

            audio_path = self.download_audio(url)
            return self.transcribe_audio(audio_path)
        except Exception as e:
            raise ValueError(f"Processing error: {str(e)}")
