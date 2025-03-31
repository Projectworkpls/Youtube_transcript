import streamlit as st
from youtube_utils import extract_video_id, get_video_info, get_youtube_transcript
from transcription import TranscriptionService
from translator import TranslationService
import os
import time

st.set_page_config(
    page_title="YouTube Multilingual Transcription",
    page_icon="🌍",
    layout="wide"
)

def initialize_services():
    try:
        os.environ["NO_PROXY"] = "*"
        os.environ["YTDLP_NO_UPDATE"] = "1"
        return TranscriptionService(), TranslationService()
    except Exception as e:
        st.error(f"Service initialization failed: {str(e)}")
        return None, None

def show_video_info(info):
    col1, col2 = st.columns([1, 2])
    with col1:
        if info.get('thumbnail_url'):
            st.image(info['thumbnail_url'], use_column_width=True)
    with col2:
        st.subheader(info.get('title', 'Unknown Title'))
        st.caption(f"by {info.get('author', 'Unknown')}")
        duration = info.get('length', 0)
        st.write(f"Duration: {duration // 60}m {duration % 60}s")
        if info.get('default_language'):
            st.write(f"Video Language: {info['default_language'].upper()}")

def main():
    trans_service, translate_service = initialize_services()
    if not trans_service or not translate_service:
        return

    with st.sidebar:
        st.header("About")
        st.write("""
        - Supports 50+ languages
        - Auto-detects video language
        - Multilingual translation
        - Works with/without subtitles
        """)

    st.title("🌍 YouTube Multilingual Transcription")
    url = st.text_input("Enter YouTube URL:", placeholder="https://youtube.com/watch?v=...")

    if url:
        try:
            with st.spinner("Analyzing video..."):
                video_id = extract_video_id(url)
                info = get_video_info(url)
                show_video_info(info)
                default_lang = info.get('default_language', 'en')

            if st.button("Generate Transcript"):
                if (yt_transcript := get_youtube_transcript(video_id, preferred_lang='en')):
                    st.session_state.transcript = yt_transcript
                    st.session_state.detected_lang = 'EN'  # YouTube provided translation
                    st.success("YouTube captions found!")
                else:
                    with st.spinner("Transcribing with AI (2-5 minutes)..."):
                        try:
                            transcript, lang = trans_service.process_video(url)
                            st.session_state.transcript = transcript
                            st.session_state.detected_lang = lang
                            st.success(f"AI transcription complete! Detected: {lang}")
                        except Exception as e:
                            error_msg = str(e)
                            if "bot" in error_msg.lower():
                                st.error("""
                                YouTube blocked this request. Try:
                                1. Waiting a few minutes
                                2. Different video
                                3. Add cookies.txt
                                """)
                            else:
                                st.error(f"Transcription failed: {error_msg}")

            if 'transcript' in st.session_state:
                with st.expander("Transcript", expanded=True):
                    if 'detected_lang' in st.session_state:
                        st.markdown(f"**Detected Language**: {st.session_state.detected_lang}")
                    st.write(st.session_state['transcript'])

                languages = translate_service.get_supported_languages()
                target_lang = st.selectbox(
                    "Translate to:",
                    options=list(languages.keys()),
                    format_func=lambda x: languages[x],
                    index=0
                )

                if st.button("Translate"):
                    with st.spinner("Translating..."):
                        try:
                            translated = translate_service.translate_text(
                                st.session_state['transcript'],
                                target_lang,
                                source_lang=st.session_state.get('detected_lang', 'auto').lower()
                            )
                            st.subheader(f"Translation ({languages[target_lang]})")
                            st.write(translated)
                        except Exception as e:
                            st.error(f"Translation error: {str(e)}")

        except Exception as e:
            st.error(f"Error processing video: {str(e)}")

if __name__ == "__main__":
    main()
