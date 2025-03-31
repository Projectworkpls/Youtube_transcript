from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp
import re
import os
from dotenv import load_dotenv
from googleapiclient.discovery import build
from tenacity import retry, stop_after_attempt, wait_exponential

load_dotenv()


# -------- Essential Function First --------
def extract_video_id(url):
    """Extract YouTube video ID from various URL formats"""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\?\/]+)',
        r'youtube.com/watch\?.*v=([^&]+)',
        r'youtube.com/shorts/([^&\?\/]+)'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError("Invalid YouTube URL")


# ------------------------------------------

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
        api_info = get_video_info_from_api(video_id)

        if api_info:
            snippet = api_info['snippet']
            content_details = api_info['contentDetails']

            # Parse duration
            duration_str = content_details['duration']
            total_seconds = 0
            time_components = {'H': 3600, 'M': 60, 'S': 1}

            for match in re.finditer(r'(\d+)([HMS])', duration_str):
                value, unit = match.groups()
                total_seconds += int(value) * time_components[unit]

            return {
                'title': snippet['title'],
                'author': snippet['channelTitle'],
                'length': total_seconds,
                'thumbnail_url': snippet['thumbnails']['high']['url'],
                'default_language': snippet.get('defaultAudioLanguage') or snippet.get('defaultLanguage')
            }

        # Fallback to yt-dlp
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                'title': info.get('title', 'Unknown Title'),
                'author': info.get('uploader', 'Unknown Author'),
                'length': int(info.get('duration', 0)),
                'thumbnail_url': info.get('thumbnail', ''),
                'default_language': info.get('language') or 'en'
            }

    except Exception as e:
        raise ValueError(f"Error fetching video info: {str(e)}")


def get_youtube_transcript(video_id, preferred_lang=None):
    """Fetch transcript with language prioritization"""
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        # 1. Try manual transcripts
        manual_transcripts = [t for t in transcript_list if not t.is_generated]
        if manual_transcripts:
            if preferred_lang:
                try:
                    return ' '.join([t['text'] for t in manual_transcripts[0].translate(preferred_lang).fetch()])
                except:
                    pass
            return ' '.join([t['text'] for t in manual_transcripts[0].fetch()])

        # 2. Try auto-generated in video's language
        generated_transcripts = [t for t in transcript_list if t.is_generated]
        if generated_transcripts:
            if preferred_lang:
                try:
                    return ' '.join([t['text'] for t in generated_transcripts[0].translate(preferred_lang).fetch()])
                except:
                    pass
            return ' '.join([t['text'] for t in generated_transcripts[0].fetch()])

        return None
    except Exception as e:
        return None
