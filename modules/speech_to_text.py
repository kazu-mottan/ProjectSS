import whisper
import streamlit as st

def transcribe(audio_path):
    model = whisper.load_model("base")
    result = model.transcribe(audio_path, language="ja")
    return result["text"] 