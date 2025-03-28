import random  # NEW
import tempfile
import os
import time
import yt_dlp
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class TranscriptionService:
    def __init__(self):
        # NEW: Bot bypass configurations
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15",
            "Mozilla/5.0 (Linux; Android 10; SM-G960U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36"
        ]
        self.proxies = os.getenv("YT_PROXIES", "").split(",") or [None]
        self.cookie_file = "cookies.txt" if os.path.exists("cookies.txt") else None

    def _get_ydl_options(self):
        """Modified to bypass bot detection"""  # NEW
        return {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(tempfile.gettempdir(), "%(id)s.%(ext)s"),
            "http_headers": {
                "User-Agent": random.choice(self.user_agents),  # NEW
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.youtube.com/",
            },
            "cookiefile": self.cookie_file,  # NEW
            "proxy": random.choice(self.proxies),  # NEW
            "retries": 10,
            "throttled_rate": "1M",  # NEW
            "sleep_interval": random.randint(1, 3),  # NEW
            "ignoreerrors": True,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
        }

    def download_audio(self, url):
        """NEW: Added proxy rotation"""
        try:
            for attempt in range(3):  # NEW: Retry with different proxies
                try:
                    ydl_opts = self._get_ydl_options()
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(url, download=True)
                        return ydl.prepare_filename(info).replace(".webm", ".mp3").replace(".m4a", ".mp3")
                except Exception as e:
                    if attempt == 2: raise
                    time.sleep(random.uniform(1, 3))  # NEW
        except Exception as e:
            raise ValueError(f"Download failed: {str(e)}")
