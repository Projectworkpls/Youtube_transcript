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
        # Deployment-safe cookie handling
        self.cookie_file = "cookies.txt" if os.path.exists("cookies.txt") else None
        self.ydl_opts = self._get_ydl_options()  # Pre-build options

    def _get_ydl_options(self):
        """Deployment-safe configuration"""
        opts = {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(tempfile.gettempdir(), "%(id)s.%(ext)s"),
            "http_headers": {
                "User-Agent": random.choice(self.user_agents),
                "Accept-Language": "en-US,en;q=0.5",
                "Referer": "https://www.youtube.com/"
            },
            "retries": 10,
            "ignoreerrors": False,  # Changed from True for better error handling
            "extract_flat": True,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
            "nocheckcertificate": True  # Important for some deployments
        }

        if self.cookie_file:
            opts["cookiefile"] = self.cookie_file

        return opts

    def download_audio(self, url):
        """Deployment-robust downloader"""
        try:
            # Initialize fresh instance each time
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)

                # Validate response
                if not info:
                    raise ValueError("Empty response from YouTube")

                filename = ydl.prepare_filename(info)

                # Ensure file exists
                if not os.path.exists(filename):
                    raise FileNotFoundError("Downloaded file not created")

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
