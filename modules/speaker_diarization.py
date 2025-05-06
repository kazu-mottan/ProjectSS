import streamlit as st
from pyannote.audio import Pipeline
import torch
import os
from typing import Dict, List, Optional
import logging
import torchaudio
import warnings

# 警告を無視する設定
warnings.filterwarnings("ignore", category=UserWarning, module="torchaudio")
warnings.filterwarnings("ignore", category=UserWarning, module="streamlit.watcher.local_sources_watcher")

class SpeakerDiarization:
    """話者分離クラス"""
    def __init__(self):
        self.pipeline = self._init_pipeline()
    
    def _init_pipeline(self) -> Pipeline:
        """パイプラインの初期化"""
        try:
            # Hugging Faceトークンの確認
            token = st.secrets["huggingface_token"]
            if not token:
                st.error("Hugging Faceトークンが設定されていません。.streamlit/secrets.tomlファイルに以下のように設定してください：\n"
                        "```toml\n"
                        "huggingface_token = \"your_token_here\"\n"
                        "```")
                return None
            
            # GPUが利用可能な場合は使用
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            
            # パイプラインの初期化
            try:
                pipeline = Pipeline.from_pretrained(
                    "pyannote/speaker-diarization-3.1",
                    use_auth_token=token
                ).to(device)
                return pipeline
            except Exception as e:
                st.error(f"パイプラインの初期化に失敗しました。以下の手順を確認してください：\n"
                        "1. Hugging Faceのアカウントでログインしているか確認\n"
                        "2. https://hf.co/pyannote/speaker-diarization-3.1 にアクセスし、使用条件に同意\n"
                        "3. トークンが正しく設定されているか確認\n"
                        f"エラー詳細: {str(e)}")
                return None
            
        except KeyError:
            st.error("Hugging Faceトークンが設定されていません。.streamlit/secrets.tomlファイルに以下のように設定してください：\n"
                    "```toml\n"
                    "huggingface_token = \"your_token_here\"\n"
                    "```")
            return None
        except Exception as e:
            st.error(f"パイプラインの初期化中にエラーが発生しました: {str(e)}")
            return None
    
    def separate_speakers(self, text: str) -> str:
        """テキストから話者を分離"""
        try:
            if not self.pipeline:
                return "パイプラインが初期化されていません。"
            
            # テキストを話者ごとに分離
            # ここでは簡単な例として、行ごとに話者を分離
            lines = text.split('\n')
            result = []
            current_speaker = None
            
            for line in lines:
                if line.strip():
                    if ':' in line:
                        speaker, content = line.split(':', 1)
                        current_speaker = speaker.strip()
                        result.append(f"{current_speaker}: {content.strip()}")
                    elif current_speaker:
                        result.append(f"{current_speaker}: {line.strip()}")
                    else:
                        result.append(f"Unknown: {line.strip()}")
            
            return '\n'.join(result)
            
        except Exception as e:
            st.error(f"話者分離中にエラーが発生しました: {str(e)}")
            return None 