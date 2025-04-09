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
        self.device = self._get_device()
        self.force_hindi = False
        self._init_model()
        
    def _get_device(self):
        if torch.cuda.is_available():
            torch.backends.cudnn.benchmark = True
            return "cuda" 
        return "cpu"
    
    def _init_model(self):
        try:
            # Start with base model for quick verification
            self.model = whisper.load_model("base", device=self.device)
            
            # Test model with dummy audio
            test_audio = torch.zeros((16000*5,))  # 5s of silence
            self.model.transcribe(test_audio)
            
            # Now load desired model
            self.model = whisper.load_model("medium" if self.device=="cuda" else "small", 
                                          device=self.device)
            if self.device == "cuda":
                self.model = self.model.half()  # FP16 optimization
                
        except Exception as e:
            logger.error(f"Model init failed: {e}")
            self.device = "cpu"
            self.model = whisper.load_model("tiny", device="cpu")

    def _get_ydl_options(self):
        return {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(tempfile.gettempdir(), '%(id)s.%(ext)s'),
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                'Accept-Language': 'en-US,en;q=0.5'
            },
            'extractor_args': {
                'youtube': {
                    'skip': ['dash', 'hls'],
                    'player_client': ['android']
                }
            },
            'retries': 10,
            'fragment_retries': 10,
            'sleep_interval': random.randint(2, 5),
            'ignoreerrors': True
        }

    @retry(stop=stop_after_attempt(3), wait=wait_random_exponential(min=1, max=30))
    def download_audio(self, url):
        try:
            ydl_opts = self._get_ydl_options()
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if not info:
                    raise ValueError("Empty response from YouTube")
                
                filename = ydl.prepare_filename(info)
                if not os.path.exists(filename):
                    raise FileNotFoundError("Downloaded file missing")
                    
                return filename
        except Exception as e:
            raise ValueError(f"Download failed: {str(e)}")

    def _transcribe_chunk(self, audio_path, start, end):
        audio = whisper.load_audio(audio_path)
        chunk = audio[start:end]
        return self.model.transcribe(
            chunk,
            fp16=(self.device == "cuda"),
            language='hi' if self.force_hindi else None,
            beam_size=5 if self.force_hindi else None,
            verbose=None
        )["text"]

    def transcribe_audio(self, audio_path):
        try:
            # Get audio duration
            audio = whisper.load_audio(audio_path)
            duration = len(audio) / 16000  # Sample rate
            
            if duration > 300:  # Chunk if >5 minutes
                chunk_size = 16000 * 300  # 5min chunks
                return " ".join(
                    self._transcribe_chunk(audio_path, i, i+chunk_size)
                    for i in range(0, len(audio), chunk_size)
                )
            else:
                result = self.model.transcribe(
                    audio_path,
                    fp16=(self.device == "cuda"),
                    language='hi' if self.force_hindi else None,
                    verbose=None
                )
                return result["text"], result.get("language", "en").upper()
                
        finally:
            if os.path.exists(audio_path):
                os.remove(audio_path)

    def process_video(self, url):
        try:
            if not any(x in urlparse(url).netloc for x in ['youtube.com', 'youtu.be']):
                raise ValueError("Invalid YouTube URL")
            
            audio_path = self.download_audio(url)
            return self.transcribe_audio(audio_path)
            
        except Exception as e:
            raise ValueError(f"Processing error: {str(e)}")
