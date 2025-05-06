import streamlit as st
import os
import tempfile
import sounddevice as sd
import numpy as np
import wave
import threading
import time
import logging

# ログの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Streamlitのaudio_recorderウィジェットを使って録音


# グローバル変数
recording = None
is_recording = False
recording_thread = None

def upload_audio():
    """
    音声ファイルをアップロードする関数
    
    Returns:
        str: アップロードされたファイルのパス
    """
    uploaded_file = st.file_uploader(
        "音声ファイル（WAV/MP3/MP4など）をアップロードしてください",
        type=["wav", "mp3", "mp4", "m4a"],
        key="audio_uploader"
    )
    
    if uploaded_file is not None:
        # 一時ファイルとして保存
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            return tmp_file.name
    return None

def record_audio(save_path="tmp/output.mp4"):
    """
    音声を録音する関数
    
    Args:
        save_path (str): 録音ファイルの保存先パス
        
    Returns:
        str: 録音ファイルのパス
    """
    global recording, is_recording, recording_thread
    
    # セッション状態の初期化
    if 'recording_status' not in st.session_state:
        st.session_state.recording_status = "idle"
    if 'saved_file_path' not in st.session_state:
        st.session_state.saved_file_path = None
    if 'save_path' not in st.session_state:
        st.session_state.save_path = os.path.abspath(save_path)
        logger.info(f"録音ファイルの保存先: {st.session_state.save_path}")
    
    # 録音状態に応じたボタン表示と処理
    if st.session_state.recording_status == "idle":
        if st.button("録音開始", key="recording_button", type="primary"):
            is_recording = True
            recording = []
            recording_thread = threading.Thread(target=record_audio_thread)
            recording_thread.start()
            st.session_state.recording_status = "recording"
            st.success("録音を開始しました")
            st.rerun()
    
    elif st.session_state.recording_status == "recording":
        st.info("🎤 録音中...")
        if st.button("録音終了", key="recording_button", type="secondary"):
            is_recording = False
            if recording_thread:
                recording_thread.join()
            st.session_state.recording_status = "stopped"
            
            # 録音データを保存
            if recording and st.session_state.save_path:
                saved_path = save_audio(recording, st.session_state.save_path)
                if saved_path:
                    st.session_state.saved_file_path = saved_path
                    st.session_state.recording_status = "saved"
                    st.success(f"録音ファイルを保存しました: {saved_path}")
                    return saved_path  # 保存されたファイルのパスを返す
                else:
                    st.error("録音ファイルの保存に失敗しました")
                    st.session_state.recording_status = "idle"
            else:
                st.error("録音データがありません")
                st.session_state.recording_status = "idle"
            st.rerun()
    
    elif st.session_state.recording_status == "saved":
        st.success(f"録音ファイルを保存しました: {st.session_state.saved_file_path}")
        if st.button("新しい録音を開始", key="new_recording_button", type="primary"):
            st.session_state.recording_status = "idle"
            st.rerun()
    
    return None  # 録音中または保存前はNoneを返す

def record_audio_thread():
    """
    録音を実行するスレッド関数
    """
    global recording, is_recording
    
    fs = 44100  # サンプリングレート
    device_id = sd.default.device[0]  # デフォルトの入力デバイスを使用
    
    while is_recording:
        # 1秒ごとに録音
        audio_chunk = sd.rec(int(1 * fs), samplerate=fs, channels=1, device=device_id)
        sd.wait()
        recording.extend(audio_chunk)

def save_audio(audio_data, save_path):
    """
    録音データをファイルに保存する関数
    
    Args:
        audio_data (list): 録音データ
        save_path (str): 保存先パス
        
    Returns:
        str: 保存されたファイルの絶対パス
    """
    try:
        # ディレクトリが存在しない場合のみ作成
        dir_path = os.path.dirname(save_path)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
            logger.info(f"ディレクトリを作成しました: {dir_path}")
        
        # 録音データをnumpy配列に変換
        audio_array = np.concatenate(audio_data)
        
        # WAVファイルとして保存
        with wave.open(save_path, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16bit
            wf.setframerate(44100)
            wf.writeframes((audio_array * 32767).astype(np.int16).tobytes())
        
        logger.info(f"録音ファイルを保存しました: {save_path}")
        return save_path
    except Exception as e:
        error_msg = f"音声ファイルの保存中にエラーが発生しました: {str(e)}"
        logger.error(error_msg)
        st.error(error_msg)
        return None 