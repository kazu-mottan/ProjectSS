import streamlit as st
import sqlite3
import pandas as pd
from typing import Dict, List, Tuple
import os
from datetime import datetime

class QuestionnaireForm:
    def __init__(self, db_path: str = "db/qa.db"):
        """問診票フォームの初期化"""
        try:
            self._initialize_database(db_path)
            self._initialize_session_state()
            self.answers = {}  # 回答を格納する辞書を初期化
        except Exception as e:
            st.error(f"初期化エラー: {str(e)}")
            self.questions = []
            self.answers = {}

    def _initialize_database(self, db_path: str):
        """データベースの初期化"""
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        
        # テーブルの存在確認
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in self.cursor.fetchall()]
        
        if 'question' not in tables:
            st.error("questionテーブルが存在しません。データベースを初期化してください。")
            self.questions = []
        else:
            self.questions = self._load_questions()

    def _initialize_session_state(self):
        """セッションステートの初期化"""
        if 'page' not in st.session_state:
            st.session_state.page = 'form'
        if 'answers' not in st.session_state:
            st.session_state.answers = {}
        if 'current_category' not in st.session_state:
            st.session_state.current_category = None
        if 'current_subcategory' not in st.session_state:
            st.session_state.current_subcategory = None

    def _load_questions(self) -> List[Dict]:
        """質問データベースから質問を読み込む"""
        try:
            df = pd.read_sql_query("SELECT * FROM question ORDER BY id", self.conn)
            return df.to_dict('records') if not df.empty else []
        except Exception as e:
            st.error(f"質問の読み込みエラー: {str(e)}")
            return []

    def render_form(self):
        """問診票フォームを表示"""
        if st.session_state.page == 'form':
            self._render_questionnaire_form()
        elif st.session_state.page == 'confirm':
            self._render_confirmation()
        elif st.session_state.page == 'complete':
            self._render_completion()

    def _render_questionnaire_form(self):
        """質問フォームを表示"""
        st.title("問診票")
        
        if not self.questions:
            st.warning("質問データがありません。データベースに質問を追加してください。")
            return

        try:
            # カテゴリごとに質問を表示
            for category, min_id in self._get_categories_with_ids():
                # カテゴリを大きな見出しで表示
                st.markdown(f"""
                    <div style='background-color: #f0f2f6; padding: 20px; border-radius: 10px; margin: 10px 0;'>
                        <h2 style='color: #1f77b4; font-size: 24px;'>{category}</h2>
                    </div>
                """, unsafe_allow_html=True)
                
                # サブカテゴリごとに質問を表示
                for subcategory, min_id in self._get_subcategories_with_ids(category):
                    # サブカテゴリを中見出しで表示
                    st.markdown(f"""
                        <div style='background-color: #e6f3ff; padding: 15px; border-radius: 8px; margin: 10px 0;'>
                            <h3 style='color: #2c3e50; font-size: 20px;'>{subcategory}</h3>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    questions = self._get_subcategory_questions(category, subcategory)
                    if not questions:
                        st.warning(f"{subcategory}に質問が設定されていません。")
                        continue

                    for question in questions:
                        self._render_question(question)
                        st.divider()

            # 回答確認ボタン
            st.markdown("""
                <div style='text-align: center; margin: 20px 0;'>
                    <button style='background-color: #4CAF50; color: white; padding: 15px 32px; 
                    text-align: center; text-decoration: none; display: inline-block; 
                    font-size: 20px; margin: 4px 2px; cursor: pointer; border-radius: 8px;'>
                        回答を確認する
                    </button>
                </div>
            """, unsafe_allow_html=True)
            
            if st.button("回答を確認する", type="primary"):
                st.session_state.page = 'confirm'
                st.session_state.answers = self.answers
                st.experimental_rerun()

        except Exception as e:
            st.error(f"フォームの表示エラー: {str(e)}")

    def _render_question(self, question: Dict):
        """個々の質問を表示"""
        try:
            question_text = question.get('question_text', '')
            answer_input = question.get('answer_input', '')
            answer_example = question.get('answer_example', '')
            field_name = question.get('項目名', '')
            question_id = str(question.get('id', ''))

            if not question_text:
                return

            # 質問文を大きな文字で表示
            st.markdown(f"""
                <div style='font-size: 18px; margin: 10px 0;'>
                    <strong>{question_text}</strong>
                </div>
            """, unsafe_allow_html=True)
            
            if answer_example:
                st.markdown(f"""
                    <div style='color: #666; font-size: 16px; margin: 5px 0;'>
                        例: {answer_example}
                    </div>
                """, unsafe_allow_html=True)

            # 一意のキーを生成
            unique_key = f"q{question_id}_{field_name}"

            # 回答形式に応じて入力フィールドを表示
            if "日付" in str(answer_input):
                self.answers[field_name] = st.date_input(
                    "回答を入力してください",
                    key=unique_key,
                    format="YYYY/MM/DD"
                )
            elif "選択" in str(answer_input):
                options = [opt.strip() for opt in str(answer_input).split(":")[1].split(",")]
                self.answers[field_name] = st.selectbox(
                    "回答を選択してください",
                    options=options,
                    key=unique_key
                )
            else:
                self.answers[field_name] = st.text_input(
                    "回答を入力してください",
                    key=unique_key
                )

        except Exception as e:
            st.error(f"質問の表示エラー: {str(e)}")

    def _render_confirmation(self):
        """回答確認画面を表示"""
        st.title("回答の確認")
        st.info("以下の内容で保存します。内容を確認してください。")
        
        # カテゴリごとに回答を表示
        for category, min_id in self._get_categories_with_ids():
            st.markdown(f"""
                <div style='background-color: #f0f2f6; padding: 20px; border-radius: 10px; margin: 10px 0;'>
                    <h2 style='color: #1f77b4; font-size: 24px;'>{category}</h2>
                </div>
            """, unsafe_allow_html=True)
            
            # サブカテゴリごとに回答を表示
            for subcategory, min_id in self._get_subcategories_with_ids(category):
                st.markdown(f"""
                    <div style='background-color: #e6f3ff; padding: 15px; border-radius: 8px; margin: 10px 0;'>
                        <h3 style='color: #2c3e50; font-size: 20px;'>{subcategory}</h3>
                    </div>
                """, unsafe_allow_html=True)
                
                # 該当する質問の回答を表示
                questions = self._get_subcategory_questions(category, subcategory)
                for question in questions:
                    field_name = question.get('項目名', '')
                    if field_name in st.session_state.answers:
                        answer = st.session_state.answers[field_name]
                        st.markdown(f"""
                            <div style='font-size: 18px; margin: 10px 0;'>
                                <strong>{question.get('question_text', '')}</strong>
                            </div>
                            <div style='font-size: 16px; margin: 5px 0;'>
                                回答: {answer}
                            </div>
                        """, unsafe_allow_html=True)
                        st.divider()

        # ボタン配置
        col1, col2 = st.columns(2)
        with col1:
            if st.button("保存する", type="primary"):
                self._save_answers_to_db()
                st.session_state.page = 'complete'
                st.experimental_rerun()
        with col2:
            if st.button("編集に戻る"):
                st.session_state.page = 'form'
                st.experimental_rerun()

    def _render_completion(self):
        """完了画面を表示"""
        st.title("回答完了")
        st.balloons()
        st.success("回答を保存しました")
        st.markdown("""
            <div style='text-align: center; margin: 20px 0;'>
                <h3 style='font-size: 24px;'>ご回答ありがとうございました。</h3>
                <p style='font-size: 18px;'>回答は正常に保存されました。</p>
            </div>
        """, unsafe_allow_html=True)
        
        if st.button("ホームに戻る", type="primary"):
            st.session_state.page = 'form'
            st.session_state.answers = {}
            st.experimental_rerun()

    def _save_answers_to_db(self):
        """回答をデータベースに保存"""
        try:
            # 必要なテーブルを作成
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS answers_input (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS answer_details (
                    id INTEGER,
                    field_name TEXT,
                    value TEXT,
                    FOREIGN KEY (id) REFERENCES answers_input(id)
                )
            """)
            
            # 回答を保存
            self.cursor.execute("INSERT INTO answers_input DEFAULT VALUES")
            answer_id = self.cursor.lastrowid
            
            # 各回答を保存
            for field_name, value in st.session_state.answers.items():
                self.cursor.execute("""
                    INSERT INTO answer_details (id, field_name, value)
                    VALUES (?, ?, ?)
                """, (answer_id, field_name, str(value)))
            
            self.conn.commit()
            
        except sqlite3.OperationalError as e:
            if "no such table" in str(e):
                st.error("回答を保存するためのテーブルが存在しません。テーブルの作成に失敗しました。")
            else:
                st.error(f"データベース操作エラー: {str(e)}")
        except Exception as e:
            st.error(f"回答の保存エラー: {str(e)}")

    def _get_categories_with_ids(self) -> List[Tuple[str, int]]:
        """カテゴリとその最小IDを取得"""
        category_info = {}
        for q in self.questions:
            category = q.get('category')
            if category:
                q_id = q.get('id', 0)
                if category not in category_info or q_id < category_info[category]:
                    category_info[category] = q_id
        return sorted(category_info.items(), key=lambda x: x[1])

    def _get_subcategories_with_ids(self, category: str) -> List[Tuple[str, int]]:
        """特定のカテゴリのサブカテゴリとその最小IDを取得"""
        subcategory_info = {}
        for q in self.questions:
            if q.get('category') == category:
                subcategory = q.get('subCategory')
                if subcategory:
                    q_id = q.get('id', 0)
                    if subcategory not in subcategory_info or q_id < subcategory_info[subcategory]:
                        subcategory_info[subcategory] = q_id
        return sorted(subcategory_info.items(), key=lambda x: x[1])

    def _get_subcategory_questions(self, category: str, subcategory: str) -> List[Dict]:
        """特定のサブカテゴリの質問を取得"""
        if not self.questions:
            return []
        return sorted(
            [q for q in self.questions if q.get('category') == category and q.get('subCategory') == subcategory],
            key=lambda x: x.get('id', 0)
        )

    def close(self):
        """データベース接続を閉じる"""
        try:
            if hasattr(self, 'conn') and self.conn:
                self.conn.close()
        except Exception as e:
            st.error(f"データベース接続のクローズエラー: {str(e)}")

def main():
    """メイン関数"""
    st.set_page_config(
        page_title="問診票",
        page_icon="📝",
        layout="wide"
    )
    
    # カスタムCSS
    st.markdown("""
        <style>
            .stButton>button {
                width: 100%;
                font-size: 20px;
                padding: 10px;
            }
            .stTextInput>div>div>input {
                font-size: 18px;
                padding: 10px;
            }
            .stSelectbox>div>div>select {
                font-size: 18px;
                padding: 10px;
            }
            .stDateInput>div>div>input {
                font-size: 18px;
                padding: 10px;
            }
            .stMarkdown {
                font-size: 18px;
            }
        </style>
    """, unsafe_allow_html=True)
    
    form = QuestionnaireForm()
    form.render_form()
    form.close()

if __name__ == "__main__":
    main() 