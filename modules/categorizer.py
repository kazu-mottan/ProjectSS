import json
import os
import streamlit as st
from typing import Dict, List, Optional
import openai
import httpx

class Categorizer:
    """カテゴリ分類クラス"""
    def __init__(self):
        try:
            self.openai_api_key = st.secrets["openai_api_key"]
            # OpenAIクライアントの初期化
            self.client = openai.OpenAI(
                api_key=self.openai_api_key,
                http_client=httpx.Client()
            )
            # question.jsonの読み込み
            with open("question.json", "r", encoding="utf-8") as f:
                self.categories = json.load(f)
        except KeyError:
            st.error("OpenAI APIキーが設定されていません。")
            self.client = None
        except FileNotFoundError:
            st.error("question.jsonが見つかりません。")
            self.categories = None
    
    def categorize(self, text: str) -> Optional[Dict[str, str]]:
        """テキストをカテゴリに分類する
        
        Args:
            text: 分類対象のテキスト
        
        Returns:
            Optional[Dict[str, str]]: カテゴリ分類結果
        """
        try:
            if not self.client or not self.categories:
                return None

            # プロンプトの作成
            prompt = f"""
            以下のテキストを、以下のカテゴリに分類してください。
            各カテゴリの内容を抽出し、JSON形式で返してください。
            
            カテゴリ:
            {json.dumps(self.categories, ensure_ascii=False, indent=2)}
            
            テキスト:
            {text}
            
            注意事項:
            1. 各カテゴリの情報が存在しない場合は空文字列("")を返してください
            2. 金額は数値のみを返してください
            3. 日付はYYYY-MM-DD形式で返してください
            4. 金融商品の種類は具体的な商品名を返してください
            """
            
            # OpenAI APIの呼び出し
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "あなたは金融機関の面談記録を分析する専門家です。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            # レスポンスの解析
            result = response.choices[0].message.content.strip()
            
            # JSON形式に変換
            try:
                categories = json.loads(result)
                return categories
            except json.JSONDecodeError:
                st.error("カテゴリ分類結果の解析に失敗しました。")
                return None
                
        except Exception as e:
            st.error(f"カテゴリ分類中にエラーが発生しました: {str(e)}")
            return None
    
    def display_categories(self, categories: Dict[str, str]):
        """カテゴリ分類結果を表示する
        
        Args:
            categories: カテゴリ分類結果
        """
        st.subheader("カテゴリ分類結果")
        
        for category, content in categories.items():
            with st.expander(category):
                if isinstance(content, dict):
                    for subcategory, value in content.items():
                        if isinstance(value, dict):
                            st.subheader(subcategory)
                            for key, val in value.items():
                                st.text_input(f"{key}", value=val)
                        else:
                            st.text_input(f"{subcategory}", value=value)
                else:
                    st.text_area("内容", value=content, height=100) 