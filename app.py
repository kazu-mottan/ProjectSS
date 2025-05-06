import streamlit as st
import pandas as pd
from modules.case_manager import QAManager
from modules.claude_vision_reader import ClaudeVisionReader
import sqlite3
import os

st.set_page_config(
    page_title="遺言作成補助システム ダッシュボード",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("遺言作成補助システム ダッシュボード")
st.markdown("""
<div style='font-size:20px; color:#555; margin-bottom:24px;'>
  サイドバーからページを選択してください。<br>
  本システムは案件管理・読み取り機能・面談・録音機能・問診票フォームなどを統合的にサポートします。
</div>
""", unsafe_allow_html=True)

# --- サマリー情報取得 ---
# 案件数・最新登録日
case_manager = QAManager()
cases = case_manager.get_cases()
case_count = len(cases)
latest_case_date = None
if cases:
    df_cases = pd.DataFrame(cases)
    if 'created_at' in df_cases.columns:
        latest_case_date = df_cases['created_at'].max()

# OCR登録数
ocr_count = 0
try:
    reader = ClaudeVisionReader()
    ocr_entries = reader.get_ocr_entries_with_images("db/qa.db", png_dir="png")
    ocr_count = len(ocr_entries)
except Exception:
    pass

# 質問数
question_count = 0
try:
    conn = sqlite3.connect("db/question.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM question")
    question_count = cursor.fetchone()[0]
    conn.close()
except Exception:
    pass

# --- サマリーカード表示 ---
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("登録案件数", f"{case_count} 件")
    if latest_case_date:
        st.caption(f"最新登録日: {latest_case_date}")
with col2:
    st.metric("OCR登録ファイル数", f"{ocr_count} 件")
with col3:
    st.metric("問診票の質問数", f"{question_count} 件")

st.markdown("""
---
<div style='font-size:18px; color:#444; margin-top:32px;'>
  <b>ご利用案内</b><br>
  ・左のサイドバーから「案件情報一覧」「読み取り機能」「面談・録音機能」「問診票フォーム」「問い合わせ」などのページに移動できます。<br>
  ・各ページでデータの登録・編集・エクスポート等が可能です。<br>
  ・データベースやテーブルの管理は管理者向けページから行えます。<br>
  <br>
  <b>サポート:</b> ご不明点や不具合は管理者までご連絡ください。
</div>
""", unsafe_allow_html=True) 