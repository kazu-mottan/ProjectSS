import streamlit as st
import openai
from typing import Dict, List, Optional
import json
import os
import httpx

class SummaryGenerator:
    """サマリー生成クラス"""
    def __init__(self):
        try:
            self.openai_api_key = st.secrets["openai_api_key"]
            # OpenAIクライアントの初期化
            self.client = openai.OpenAI(
                api_key=self.openai_api_key,
                http_client=httpx.Client()
            )
        except KeyError:
            st.error("OpenAI APIキーが設定されていません。")
            self.client = None
    
    def generate_summary(self, text: str) -> Optional[str]:
        """テキストからサマリーを生成する
        
        Args:
            text: サマリー生成対象のテキスト
        
        Returns:
            Optional[str]: 生成されたサマリー
        """
        try:
            if not self.client:
                return None

            # プロンプトの作成
            prompt = f"""
            以下の会話ログを、以下の要件に従って要約してください：

            1. 不要な言い回しや重複を削除
            2. 重要な情報を簡潔にまとめる
            3. 自然な日本語で読みやすくする
            4. 箇条書きや見出しを使用して構造化する
            5. 金融機関の面談記録として適切な形式にする

            会話ログ:
            {text}
            """
            
            # OpenAI APIの呼び出し
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "あなたは金融機関の面談記録を要約する専門家です。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            # レスポンスの解析
            summary = response.choices[0].message.content.strip()
            return summary
                
        except Exception as e:
            st.error(f"サマリー生成中にエラーが発生しました: {str(e)}")
            return None
    
    def display_summary(self, summary: str):
        """サマリーを表示する
        
        Args:
            summary: 生成されたサマリー
        """
        st.subheader("会話サマリー")
        st.markdown(summary) 