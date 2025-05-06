import sqlite3
import pandas as pd

# CSVファイルを読み込む（エンコーディングを指定）
df = pd.read_csv('テスト_質問-回答(test_easy).csv', encoding='shift-jis')

# データベースに接続
conn = sqlite3.connect('question.db')
cursor = conn.cursor()

# テーブルを作成
cursor.execute('''
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY,
        category TEXT,
        subcategory TEXT,
        question_text TEXT,
        answer_format TEXT,
        field_name TEXT,
        answer_example TEXT,
        notes TEXT
    )
''')

# データを挿入
for _, row in df.iterrows():
    cursor.execute('''
        INSERT INTO questions (id, category, subcategory, question_text, answer_format, field_name, answer_example, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        row.iloc[0] if pd.notna(row.iloc[0]) else None,
        row.iloc[1] if pd.notna(row.iloc[1]) else None,
        row.iloc[2] if pd.notna(row.iloc[2]) else None,
        row.iloc[3] if pd.notna(row.iloc[3]) else None,
        row.iloc[4] if pd.notna(row.iloc[4]) else None,
        row.iloc[5] if pd.notna(row.iloc[5]) else None,
        row.iloc[6] if pd.notna(row.iloc[6]) else None,
        row.iloc[7] if pd.notna(row.iloc[7]) else None
    ))

# 変更をコミット
conn.commit()

# 接続を閉じる
conn.close()

print("データのインポートが完了しました。") 