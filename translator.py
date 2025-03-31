from deep_translator import GoogleTranslator
from typing import Dict, Optional
import time
import requests
from tenacity import retry, stop_after_attempt, wait_exponential


class TranslationService:
    def __init__(self):
        self.supported_languages = {
            'en': 'English',
            'es': 'Spanish',
            'fr': 'French',
            'de': 'German',
            'it': 'Italian',
            'pt': 'Portuguese',
            'ru': 'Russian',
            'ja': 'Japanese',
            'ko': 'Korean',
            'zh-cn': 'Chinese (Simplified)',
            'hi': 'Hindi',
            'ar': 'Arabic',
            'bn': 'Bengali',
            'ur': 'Urdu',
            'te': 'Telugu',
            'ta': 'Tamil',
            'mr': 'Marathi',
            'gu': 'Gujarati'
        }
        self.lang_code_map = {
            'zh-cn': 'zh-CN',
            'bn': 'bn',
            'gu': 'gu',
            'mr': 'mr',
            'te': 'te',
            'ta': 'ta',
            'ur': 'ur'
        }

    def get_supported_languages(self) -> Dict[str, str]:
        return self.supported_languages

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def translate_text(self, text: Optional[str], target_lang: str, source_lang: str = 'auto') -> str:
        if not text or not isinstance(text, str):
            raise ValueError("Invalid input: text must be a non-empty string")

        text = text.strip()
        if not text:
            raise ValueError("Invalid input: text contains only whitespace")

        if target_lang not in self.supported_languages:
            raise ValueError(f"Language code '{target_lang}' not supported")

        if target_lang == 'en' and source_lang == 'en':
            return text

        translated_target_lang = self.lang_code_map.get(target_lang, target_lang)
        MAX_CHUNK_LENGTH = 4999
        chunks = [text[i:i + MAX_CHUNK_LENGTH] for i in range(0, len(text), MAX_CHUNK_LENGTH)]

        translated_chunks = []
        translator = GoogleTranslator(source=source_lang, target=translated_target_lang)

        for chunk in chunks:
            try:
                translated = translator.translate(text=chunk)
                translated_chunks.append(translated)
                if len(chunks) > 1:
                    time.sleep(0.5)
            except Exception as e:
                raise ValueError(f"Translation error: {str(e)}")

        return ' '.join(translated_chunks)

    def detect_language(self, text: str) -> str:
        try:
            translator = GoogleTranslator(source='auto', target='en')
            return translator.detect(text).lower()
        except Exception as e:
            return 'en'  # Fallback to English
