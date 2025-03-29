import streamlit as st
from youtube_utils import extract_video_id, get_video_info, get_youtube_transcript
from transcription import TranscriptionService
from translator import TranslationService
import os

# MUST be the first Streamlit command
st.set_page_config(
    page_title="YouTube Transcription & Translation",
    page_icon="🎥",
    layout="wide"
)


def initialize_services():
    """Initialize services with error handling"""
    try:
        return TranscriptionService(), TranslationService()
    except Exception as e:
        st.error(f"Service initialization failed: {str(e)}")
        return None, None


def main():
    # Initialize services
    trans_service, transle_service = initialize_services()

    if not trans_service or not transle_service:
        return

    # Sidebar - must come before any other UI elements
    with st.sidebar:
        st.header("About")
        st.write("""
        - Generates transcripts from YouTube videos
        - Supports both YouTube captions and AI transcription
        - Translates to multiple languages
        """)

    # Main content
    st.title("YouTube Video Transcription & Translation")

    url = st.text_input("Enter YouTube URL:", placeholder="https://youtube.com/watch?v=...")

    if url:
        try:
            with st.spinner("Fetching video info..."):
                video_id = extract_video_id(url)
                info = get_video_info(url)

            # Display video info
            col1, col2 = st.columns([1, 2])
            with col1:
                if info.get('thumbnail_url'):
                    st.image(info['thumbnail_url'], use_column_width=True)
            with col2:
                st.subheader(info.get('title', 'Unknown Title'))
                st.caption(f"by {info.get('author', 'Unknown')}")

                duration = info.get('length', 0)
                st.write(f"Duration: {duration // 60}m {duration % 60}s")

            # Transcript generation
            if st.button("Generate Transcript"):
                if (yt_transcript := get_youtube_transcript(video_id)):
                    st.session_state.transcript = yt_transcript
                    st.success("YouTube captions found!")
                else:
                    with st.spinner("Transcribing with AI..."):
                        try:
                            st.session_state.transcript = trans_service.process_video(url)
                            st.success("AI transcription complete!")
                        except Exception as e:
                            st.error(f"Transcription failed: {str(e)}")

            # Display and translation
            if 'transcript' in st.session_state:
                with st.expander("Transcript", expanded=True):
                    st.write(st.session_state['transcript'])

                if transle_service:
                    languages = transle_service.get_supported_languages()
                    target_lang = st.selectbox(
                        "Translate to:",
                        options=list(languages.keys()),
                        format_func=lambda x: languages[x]
                    )

                    if st.button("Translate"):
                        with st.spinner("Translating..."):
                            translated = transle_service.translate_text(
                                st.session_state['transcript'],
                                target_lang
                            )
                            st.subheader(f"Translation ({languages[target_lang]})")
                            st.write(translated)

        except Exception as e:
            st.error(f"Error processing video: {str(e)}")


if __name__ == "__main__":
    main()
