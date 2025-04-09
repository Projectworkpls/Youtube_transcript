import streamlit as st
from youtube_utils import extract_video_id, get_video_info, get_youtube_transcript
from transcription import TranscriptionService
from translator import TranslationService
import os
import time

st.set_page_config(
    page_title="YouTube Multilingual Transcriber",
    page_icon="🎙️",
    layout="wide"
)

def init_services():
    os.environ["NO_PROXY"] = "*"
    os.environ["YTDLP_NO_UPDATE"] = "1"
    return TranscriptionService(), TranslationService()

def show_video_info(info):
    col1, col2 = st.columns([1, 2])
    with col1:
        if info.get('thumbnail_url'):
            st.image(info['thumbnail_url'], width=300)
    with col2:
        st.subheader(info.get('title', 'Unknown Title'))
        st.caption(f"Channel: {info.get('author', 'Unknown')}")
        st.write(f"Duration: {info['length']//60}m {info['length']%60}s")
        if lang := info.get('default_language'):
            st.write(f"Detected Language: {lang.upper()}")

def main():
    trans_service, translate_service = init_services()
    
    st.title("YouTube Video Transcriber")
    url = st.text_input("Enter YouTube URL:", placeholder="https://youtube.com/watch?v=...")
    
    if url:
        try:
            with st.spinner("Fetching video info..."):
                video_id = extract_video_id(url)
                info = get_video_info(url)
                show_video_info(info)
                
            # Language detection options
            with st.expander("Advanced Options"):
                trans_service.force_hindi = st.checkbox("Force Hindi Detection")
                if st.checkbox("Use Large Model (Slower but Accurate)"):
                    trans_service.model = whisper.load_model("large", device=trans_service.device)
            
            if st.button("Generate Transcript"):
                if (yt_transcript := get_youtube_transcript(video_id, preferred_lang='en')):
                    st.session_state.transcript = yt_transcript
                    st.success("YouTube captions found!")
                else:
                    with st.spinner("Transcribing with AI (2-5 mins)..."):
                        try:
                            transcript, lang = trans_service.process_video(url)
                            st.session_state.transcript = transcript
                            st.session_state.detected_lang = lang
                            st.success(f"Transcription complete! Detected: {lang}")
                        except Exception as e:
                            if "cookie" in str(e).lower():
                                st.error("""
                                Age-restricted content detected. Solutions:
                                1. Add cookies.txt file
                                2. Try different video
                                """)
                            else:
                                st.error(f"Transcription failed: {str(e)}")

            if 'transcript' in st.session_state:
                with st.expander("Transcript", expanded=True):
                    st.text_area("Transcript", 
                               st.session_state['transcript'],
                               height=300)
                
                # Translation section
                languages = translate_service.get_supported_languages()
                target_lang = st.selectbox(
                    "Translate to:",
                    options=list(languages.keys()),
                    format_func=lambda x: languages[x]
                )
                
                if st.button("Translate"):
                    with st.spinner(f"Translating to {languages[target_lang]}..."):
                        try:
                            translated = translate_service.translate_text(
                                st.session_state['transcript'],
                                target_lang,
                                source_lang=st.session_state.get('detected_lang', 'auto').lower()
                            )
                            st.subheader(f"Translation ({languages[target_lang]})")
                            st.text_area("", translated, height=300)
                        except Exception as e:
                            st.error(f"Translation error: {str(e)}")
                            
        except Exception as e:
            st.error(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
