from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp
import re
import os
from dotenv import load_dotenv
from googleapiclient.discovery import build
from tenacity import retry, stop_after_attempt, wait_exponential

load_dotenv()

def extract_video_id(url):
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\?\/]+)',
        r'youtube.com/watch\?.*v=([^&]+)',
        r'youtube.com/shorts/([^&\?\/]+)'
    ]
    for pattern in patterns:
        if match := re.search(pattern, url):
            return match.group(1)
    raise ValueError("Invalid YouTube URL")

def get_youtube_api_client():
    if api_key := os.getenv('YOUTUBE_API_KEY'):
        return build('youtube', 'v3', developerKey=api_key)
    return None

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def get_video_info_from_api(video_id):
    if not (youtube := get_youtube_api_client()):
        return None
    try:
        request = youtube.videos().list(part="snippet,contentDetails", id=video_id)
        return request.execute().get('items', [{}])[0]
    except Exception:
        return None

def get_video_info(url):
    try:
        video_id = extract_video_id(url)
        if api_info := get_video_info_from_api(video_id):
            snippet = api_info['snippet']
            content_details = api_info['contentDetails']
            duration = sum(
                int(num[:-1]) * {"h": 3600, "m": 60, "s": 1}[unit.lower()]
                for num, unit in re.findall(r'(\d+)(H|M|S)', content_details['duration'])
            )
            return {
                'title': snippet['title'],
                'author': snippet['channelTitle'],
                'length': duration,
                'thumbnail_url': snippet['thumbnails']['high']['url']
            }

        # Fallback to yt-dlp
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                'title': info.get('title', 'Unknown Title'),
                'author': info.get('uploader', 'Unknown Author'),
                'length': info.get('duration', 0),
                'thumbnail_url': info.get('thumbnail', '')
            }
    except Exception as e:
        raise ValueError(f"Error fetching video info: {str(e)}")

def get_youtube_transcript(video_id):
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        try: return ' '.join([t['text'] for t in transcript_list.find_transcript(['en']).fetch()])
        except: return None
    except Exception:
        return None