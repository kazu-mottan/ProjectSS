import streamlit as st
import tempfile
import whisper
from modules.categorizer import Categorizer
from modules.summary_generator import SummaryGenerator
from st_audiorecorder import st_audiorecorder

st.set_page_config(page_title="面談・録音機能", page_icon="🎤")
st.title("面談・録音機能")

audio_processor = whisper.load_model("base")
categorizer = Categorizer()
summary_generator = SummaryGenerator()

mode = st.radio("操作モードを選択", ("音声アップロード", "音声録音"), horizontal=True)

if mode == "音声アップロード":
    uploaded_file = st.file_uploader("音声ファイルをアップロードしてください（mp3, wav, m4a など）", type=["mp3", "wav", "m4a"])
    if uploaded_file is not None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            tmp_file.write(uploaded_file.read())
            tmp_path = tmp_file.name
        st.info("音声ファイルを文字起こし中...")
        result = audio_processor.transcribe(tmp_path, language="ja")
        transcription = result["text"]
        st.success("文字起こし結果：")
        st.write(transcription)
elif mode == "音声録音":
    st.info("下のボタンで録音を開始・停止してください。録音後、自動で文字起こしされます。")
    audio_data = st_audiorecorder("録音開始", "録音停止")
    if audio_data is not None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            tmp_file.write(audio_data)
            tmp_path = tmp_file.name
        st.info("録音データを文字起こし中...")
        result = audio_processor.transcribe(tmp_path, language="ja")
        transcription = result["text"]
        st.success("文字起こし結果：")
        st.write(transcription) 