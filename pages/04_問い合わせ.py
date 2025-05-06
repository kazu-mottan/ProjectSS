import streamlit as st
import pandas as pd
import os
from datetime import datetime

st.set_page_config(page_title="問い合わせ", page_icon="✉️")
st.title("問い合わせ")

st.markdown("""
ご意見・ご質問・不具合報告などがありましたら、下記フォームよりご連絡ください。
""")

with st.form("contact_form"):
    name = st.text_input("お名前", max_chars=50)
    email = st.text_input("メールアドレス", max_chars=100)
    message = st.text_area("お問い合わせ内容", height=150)
    submitted = st.form_submit_button("送信")

if submitted:
    if not name or not email or not message:
        st.error("全ての項目を入力してください。")
    else:
        # 保存先（CSVファイル）
        save_dir = "db"
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, "contact_inquiries.csv")
        # 既存データの読み込み
        if os.path.exists(save_path):
            df = pd.read_csv(save_path)
        else:
            df = pd.DataFrame(columns=["timestamp", "name", "email", "message"])
        # 新規データ追加
        new_row = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "name": name,
            "email": email,
            "message": message
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        df.to_csv(save_path, index=False)
        st.success("お問い合わせ内容を送信しました。ありがとうございました。")
        st.balloons()
        st.markdown("ホーム画面へ戻る場合はサイドバーから選択してください。") 