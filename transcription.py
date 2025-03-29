import whisper
import torch
import tempfile
import os
import yt_dlp
import random
import logging
from urllib.parse import urlparse
from tenacity import retry, stop_after_attempt, wait_random_exponential

logger = logging.getLogger(__name__)


class TranscriptionService:
    def __init__(self):
        self.model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15"
        ]
        self.cookie_file = "cookies.txt" if os.path.exists("cookies.txt") else None
        self.proxies = self._load_proxies()

    def _load_proxies(self):
        """Load proxies from environment variables"""
        proxy_str = os.getenv("YT_PROXIES", "")
        return [p.strip() for p in proxy_str.split(",") if p.strip()] or [None]

    def _get_ydl_options(self):
        """Anti-bot configuration with fallbacks"""
        opts = {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(tempfile.gettempdir(), "yt_%(id)s.%(ext)s"),
            "http_headers": {
                "User-Agent": random.choice(self.user_agents),
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.youtube.com/",
                "X-Forwarded-For": f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}"
            },
            "retries": 15,
            "fragment_retries": 15,
            "ignoreerrors": False,
            "extract_flat": "in_playlist",
            "nocheckcertificate": True,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
            "throttled_rate": "1M",
            "sleep_interval": random.randint(2, 5),
        }

        if self.cookie_file:
            opts["cookiefile"] = self.cookie_file
        if self.proxies[0]:
            opts["proxy"] = random.choice(self.proxies)

        return opts

    @retry(stop=stop_after_attempt(3), wait=wait_random_exponential(min=1, max=10))
    def download_audio(self, url):
        """Robust download with retry logic"""
        try:
            ydl_opts = self._get_ydl_options()
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if not info:
                    raise ValueError("Empty response from YouTube")

                filename = ydl.prepare_filename(info)
                valid_extensions = ['.webm', '.m4a', '.mp4']
                for ext in valid_extensions:
                    if filename.endswith(ext):
                        return filename

                raise ValueError("Invalid file format downloaded")

        except Exception as e:
            raise ValueError(f"Download failed: {str(e)}")

    def transcribe_audio(self, audio_path):
        """Whisper transcription with cleanup"""
        try:
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"Audio file missing: {audio_path}")

            if self.model is None:
                torch.cuda.empty_cache() if self.device == "cuda" else None
                self.model = whisper.load_model("small", device=self.device)

            result = self.model.transcribe(
                audio_path,
                fp16=(self.device == "cuda"),
                language="en",
                verbose=False
            )
            return result["text"]

        finally:
            if os.path.exists(audio_path):
                os.remove(audio_path)

    def process_video(self, url):
        """Main processing pipeline"""
        try:
            parsed = urlparse(url)
            if not any(x in parsed.netloc for x in ['youtube.com', 'youtu.be']):
                raise ValueError("Invalid YouTube URL")

            audio_path = self.download_audio(url)
            return self.transcribe_audio(audio_path)

        except Exception as e:
            raise ValueError(f"Processing error: {str(e)}")
