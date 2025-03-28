import random
import tempfile
import os
import time
import yt_dlp
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class TranscriptionService:
    def __init__(self):
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15...",
        ]
        self.proxy_list = os.getenv("YT_PROXIES", "").split(",") or [None]
        self.cookie_file = "cookies.txt" if os.path.exists("cookies.txt") else None

    def _get_ydl_options(self):
        return {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(tempfile.gettempdir(), "%(id)s.%(ext)s"),
            "http_headers": {
                "User-Agent": random.choice(self.user_agents),
                "Accept-Language": "en-US,en;q=0.5",
                "Referer": "https://www.youtube.com/",
            },
            "cookiefile": self.cookie_file,
            "proxy": random.choice(self.proxy_list),
            "retries": 10,
            "throttled_rate": "1M",
            "sleep_interval": random.randint(1, 3),
            "ignoreerrors": True,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
        }

    def download_audio(self, url):
        try:
            for attempt in range(3):
                try:
                    ydl_opts = self._get_ydl_options()
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(url, download=True)
                        return ydl.prepare_filename(info).replace(".webm", ".mp3").replace(".m4a", ".mp3")
                except Exception as e:
                    if attempt == 2: raise
                    time.sleep(random.uniform(1, 3))
        except Exception as e:
            raise ValueError(f"Download failed: {str(e)}")

    def transcribe_audio(self, audio_path):
        try:
            # Your existing transcription logic
            # ...
            return "Dummy transcription text"  # Replace with actual implementation
        except Exception as e:
            if os.path.exists(audio_path):
                os.remove(audio_path)
            raise ValueError(f"Transcription error: {str(e)}")

    def process_video(self, url):  # THIS WAS MISSING
        """Main processing method"""
        try:
            if not url.startswith(('http://', 'https://')):
                url = f'https://{url}'

            parsed = urlparse(url)
            if not any(x in parsed.netloc for x in ['youtube.com', 'youtu.be']):
                raise ValueError("Invalid YouTube URL")

            audio_path = self.download_audio(url)
            return self.transcribe_audio(audio_path)

        except Exception as e:
            raise ValueError(f"Processing error: {str(e)}")
