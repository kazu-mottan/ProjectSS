import sqlite3
import pandas as pd
from typing import List, Dict, Optional
import streamlit as st
import warnings
import io
import os
import glob

# 警告を無視する設定
warnings.filterwarnings("ignore", category=UserWarning, module="torchaudio")

# データベースディレクトリの設定
DB_DIR = "../db"
DEFAULT_CASES_DB = os.path.join(DB_DIR, "cases.db")
DEFAULT_QUESTIONS_DB = os.path.join(DB_DIR, "question.db")

class DBManager:
    """データベース操作クラス"""
    def __init__(self, db_path: str = DEFAULT_CASES_DB):
        self.db_path = db_path
        self.conn = None
        self.cursor = None

    def connect(self):
        """データベースに接続"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            return True
        except Exception as e:
            st.error(f"データベース接続エラー: {str(e)}")
            return False

    def close(self):
        """データベース接続を閉じる"""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None

    def import_from_excel(self, excel_file: io.BytesIO, sheet_name: str = None) -> bool:
        """Excelファイルからデータをインポート"""
        try:
            # Excelファイルを読み込む
            df = pd.read_excel(excel_file, sheet_name=sheet_name)
            total_rows = len(df)
            total_columns = len(df.columns)
            
            # 列名と行番号の情報を表示
            st.info(f"Excelファイルの情報:")
            st.write(f"- 列名: {', '.join(df.columns)}")
            st.write(f"- 列数: {total_columns}")
            st.write(f"- 行数: {total_rows}")
            
            # データのプレビューを表示
            st.subheader("データのプレビュー")
            st.dataframe(df.head())
            
            # データベースのテーブル名を取得
            table_name = 'cases' if self.db_path == DEFAULT_CASES_DB else 'questions'
            
            # 既存のデータを削除
            self.cursor.execute(f"DELETE FROM {table_name}")
            
            # 新しいデータを挿入
            for _, row in df.iterrows():
                columns = ', '.join(df.columns)
                placeholders = ', '.join(['?' for _ in df.columns])
                values = tuple(row)
                
                query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
                self.cursor.execute(query, values)
            
            self.conn.commit()
            st.success(f"合計 {total_rows} 行のデータをインポートしました")
            return True
        except Exception as e:
            st.error(f"Excelからのインポートエラー: {str(e)}")
            return False

    def export_to_excel(self) -> bytes:
        """データベースの内容をExcelファイルとしてエクスポート"""
        try:
            # データベースのテーブル名を取得
            table_name = 'cases' if self.db_path == DEFAULT_CASES_DB else 'questions'
            
            # データを読み込む
            df = pd.read_sql_query(f"SELECT * FROM {table_name}", self.conn)
            
            # Excelファイルとして出力
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name=table_name, index=False)
            return output.getvalue()
        except Exception as e:
            st.error(f"Excelへのエクスポートエラー: {str(e)}")
            return None

    def get_all_cases(self) -> pd.DataFrame:
        """全案件を取得"""
        try:
            df = pd.read_sql_query("SELECT * FROM cases", self.conn)
            return df
        except Exception as e:
            st.error(f"データ取得エラー: {str(e)}")
            return pd.DataFrame()

    def get_case(self, case_id: int) -> Optional[Dict]:
        """特定の案件を取得"""
        try:
            self.cursor.execute("SELECT * FROM cases WHERE id = ?", (case_id,))
            row = self.cursor.fetchone()
            if row:
                columns = [description[0] for description in self.cursor.description]
                return dict(zip(columns, row))
            return None
        except Exception as e:
            st.error(f"案件取得エラー: {str(e)}")
            return None

    def add_case(self, case_data: Dict) -> bool:
        """案件を追加"""
        try:
            columns = ', '.join(case_data.keys())
            placeholders = ', '.join(['?' for _ in case_data])
            values = tuple(case_data.values())
            
            query = f"INSERT INTO cases ({columns}) VALUES ({placeholders})"
            self.cursor.execute(query, values)
            self.conn.commit()
            return True
        except Exception as e:
            st.error(f"案件追加エラー: {str(e)}")
            return False

    def update_case(self, case_id: int, case_data: Dict) -> bool:
        """案件を更新"""
        try:
            set_clause = ', '.join([f"{key} = ?" for key in case_data.keys()])
            values = tuple(case_data.values()) + (case_id,)
            
            query = f"UPDATE cases SET {set_clause} WHERE id = ?"
            self.cursor.execute(query, values)
            self.conn.commit()
            return True
        except Exception as e:
            st.error(f"案件更新エラー: {str(e)}")
            return False

    def delete_case(self, case_id: int) -> bool:
        """案件を削除"""
        try:
            self.cursor.execute("DELETE FROM cases WHERE id = ?", (case_id,))
            self.conn.commit()
            return True
        except Exception as e:
            st.error(f"案件削除エラー: {str(e)}")
            return False

    def search_cases(self, search_term: str) -> pd.DataFrame:
        """案件を検索"""
        try:
            query = """
                SELECT * FROM cases 
                WHERE company_name LIKE ? 
                OR branch_number LIKE ? 
                OR cif_name LIKE ? 
                OR case_type LIKE ? 
                OR fa_name LIKE ? 
                OR staff_name LIKE ?
            """
            search_pattern = f"%{search_term}%"
            params = [search_pattern] * 6
            df = pd.read_sql_query(query, self.conn, params=params)
            return df
        except Exception as e:
            st.error(f"検索エラー: {str(e)}")
            return pd.DataFrame()

    # 質問データベース関連のメソッド
    def get_all_questions(self) -> pd.DataFrame:
        """全質問を取得"""
        try:
            df = pd.read_sql_query("SELECT * FROM questions", self.conn)
            return df
        except Exception as e:
            st.error(f"質問データ取得エラー: {str(e)}")
            return pd.DataFrame()

    def get_question(self, question_id: int) -> Optional[Dict]:
        """特定の質問を取得"""
        try:
            self.cursor.execute("SELECT * FROM questions WHERE id = ?", (question_id,))
            row = self.cursor.fetchone()
            if row:
                columns = [description[0] for description in self.cursor.description]
                return dict(zip(columns, row))
            return None
        except Exception as e:
            st.error(f"質問取得エラー: {str(e)}")
            return None

    def add_question(self, question_data: Dict) -> bool:
        """質問を追加"""
        try:
            columns = ', '.join(question_data.keys())
            placeholders = ', '.join(['?' for _ in question_data])
            values = tuple(question_data.values())
            
            query = f"INSERT INTO questions ({columns}) VALUES ({placeholders})"
            self.cursor.execute(query, values)
            self.conn.commit()
            return True
        except Exception as e:
            st.error(f"質問追加エラー: {str(e)}")
            return False

    def update_question(self, question_id: int, question_data: Dict) -> bool:
        """質問を更新"""
        try:
            set_clause = ', '.join([f"{key} = ?" for key in question_data.keys()])
            values = tuple(question_data.values()) + (question_id,)
            
            query = f"UPDATE questions SET {set_clause} WHERE id = ?"
            self.cursor.execute(query, values)
            self.conn.commit()
            return True
        except Exception as e:
            st.error(f"質問更新エラー: {str(e)}")
            return False

    def delete_question(self, question_id: int) -> bool:
        """質問を削除"""
        try:
            self.cursor.execute("DELETE FROM questions WHERE id = ?", (question_id,))
            self.conn.commit()
            return True
        except Exception as e:
            st.error(f"質問削除エラー: {str(e)}")
            return False

    def search_questions(self, search_term: str) -> pd.DataFrame:
        """質問を検索"""
        try:
            query = """
                SELECT * FROM questions 
                WHERE category LIKE ? 
                OR subcategory LIKE ? 
                OR question_text LIKE ? 
                OR answer_format LIKE ? 
                OR field_name LIKE ? 
                OR answer_example LIKE ?
            """
            search_pattern = f"%{search_term}%"
            params = [search_pattern] * 6
            df = pd.read_sql_query(query, self.conn, params=params)
            return df
        except Exception as e:
            st.error(f"質問検索エラー: {str(e)}")
            return pd.DataFrame()

    def create_new_database(self, db_name: str, db_type: str) -> bool:
        """新しいデータベースを作成"""
        try:
            # dbディレクトリが存在しなければエラー
            if not os.path.isdir(DB_DIR):
                st.error(f"データベースディレクトリ {DB_DIR} が存在しません。")
                return False
            db_filename = os.path.basename(db_name)
            db_path = os.path.join(DB_DIR, db_filename)
            # データベースファイルのパスを設定
            self.db_path = db_path
            # データベースに接続
            if not self.connect():
                return False
            
            # テーブルを作成
            if db_type == "案件データベース":
                self.cursor.execute("""
                    CREATE TABLE cases (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        company_name TEXT,
                        branch_number TEXT,
                        cif_name TEXT,
                        case_type TEXT,
                        fa_name TEXT,
                        staff_name TEXT
                    )
                """)
            else:  # 質問データベース
                self.cursor.execute("""
                    CREATE TABLE questions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        category TEXT,
                        subcategory TEXT,
                        question_text TEXT,
                        answer_format TEXT,
                        field_name TEXT,
                        answer_example TEXT,
                        notes TEXT
                    )
                """)
            
            self.conn.commit()
            return True
        except Exception as e:
            st.error(f"データベース作成エラー: {str(e)}")
            return False

    def create_table_from_excel(self, excel_file: io.BytesIO, table_name: str) -> bool:
        """Excelファイルからテーブルを作成し、データをインポート"""
        try:
            # Excelファイルを読み込む
            df = pd.read_excel(excel_file)
            total_rows = len(df)
            total_columns = len(df.columns)
            
            # 列名と行番号の情報を表示
            st.info(f"Excelファイルの情報:")
            st.write(f"- 列名: {', '.join(df.columns)}")
            st.write(f"- 列数: {total_columns}")
            st.write(f"- 行数: {total_rows}")
            
            # データのプレビューを表示
            st.subheader("データのプレビュー")
            st.dataframe(df.head())
            
            # 既存のテーブルを削除（存在する場合）
            self.cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
            
            # テーブル作成SQLを生成
            columns = []
            for col in df.columns:
                # データ型を推測
                sample_value = df[col].iloc[0]
                if pd.api.types.is_integer_dtype(df[col]):
                    col_type = "INTEGER"
                elif pd.api.types.is_float_dtype(df[col]):
                    col_type = "REAL"
                elif pd.api.types.is_datetime64_any_dtype(df[col]):
                    col_type = "TEXT"
                else:
                    col_type = "TEXT"
                
                columns.append(f"{col} {col_type}")
            
            # テーブル作成
            create_table_sql = f"""
                CREATE TABLE {table_name} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    {', '.join(columns)}
                )
            """
            self.cursor.execute(create_table_sql)
            
            # データを挿入
            for _, row in df.iterrows():
                columns = ', '.join(df.columns)
                placeholders = ', '.join(['?' for _ in df.columns])
                values = tuple(row)
                
                query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
                self.cursor.execute(query, values)
            
            self.conn.commit()
            st.success(f"テーブル '{table_name}' を作成し、合計 {total_rows} 行のデータをインポートしました")
            return True
        except Exception as e:
            st.error(f"テーブル作成エラー: {str(e)}")
            return False

    def get_table_info(self) -> List[str]:
        """データベース内のテーブル情報を取得"""
        try:
            self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in self.cursor.fetchall()]
            return tables
        except Exception as e:
            st.error(f"テーブル情報取得エラー: {str(e)}")
            return []

    def get_table_structure(self, table_name: str) -> pd.DataFrame:
        """テーブルの構造を取得"""
        try:
            self.cursor.execute(f"PRAGMA table_info({table_name})")
            columns = self.cursor.fetchall()
            df = pd.DataFrame(columns, columns=['cid', 'name', 'type', 'notnull', 'dflt_value', 'pk'])
            return df
        except Exception as e:
            st.error(f"テーブル構造取得エラー: {str(e)}")
            return pd.DataFrame()

    def get_table_data(self, table_name: str) -> pd.DataFrame:
        """テーブルのデータを取得"""
        try:
            df = pd.read_sql_query(f"SELECT * FROM {table_name}", self.conn)
            return df
        except Exception as e:
            st.error(f"テーブルデータ取得エラー: {str(e)}")
            return pd.DataFrame()

    def delete_table(self, table_name: str) -> bool:
        """テーブルを削除"""
        try:
            # テーブルの存在確認
            self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
            if not self.cursor.fetchone():
                st.error(f"テーブル '{table_name}' は存在しません")
                return False
            
            # テーブルを削除
            self.cursor.execute(f"DROP TABLE {table_name}")
            self.conn.commit()
            st.success(f"テーブル '{table_name}' を削除しました")
            return True
        except Exception as e:
            st.error(f"テーブル削除エラー: {str(e)}")
            return False

    def create_table(self, table_name: str, columns: List[Dict[str, str]]) -> bool:
        """新しいテーブルを作成"""
        try:
            # テーブル名の存在確認
            self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
            if self.cursor.fetchone():
                st.error(f"テーブル '{table_name}' は既に存在します")
                return False
            
            # カラム定義の生成
            column_definitions = []
            for col in columns:
                col_name = col['name']
                col_type = col['type']
                col_constraints = col.get('constraints', '')
                column_definitions.append(f"{col_name} {col_type} {col_constraints}")
            
            # テーブル作成SQLの実行
            create_sql = f"""
                CREATE TABLE {table_name} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    {', '.join(column_definitions)}
                )
            """
            self.cursor.execute(create_sql)
            self.conn.commit()
            st.success(f"テーブル '{table_name}' を作成しました")
            return True
        except Exception as e:
            st.error(f"テーブル作成エラー: {str(e)}")
            return False

    def add_column(self, table_name: str, column_name: str, column_type: str, constraints: str = "") -> bool:
        """既存テーブルにカラムを追加"""
        try:
            sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type} {constraints}"
            self.cursor.execute(sql)
            self.conn.commit()
            st.success(f"カラム '{column_name}' を追加しました")
            return True
        except Exception as e:
            st.error(f"カラム追加エラー: {str(e)}")
            return False

    def drop_column(self, table_name: str, column_name: str) -> bool:
        """既存テーブルからカラムを削除（SQLite 3.35以降対応）"""
        try:
            sql = f"ALTER TABLE {table_name} DROP COLUMN {column_name}"
            self.cursor.execute(sql)
            self.conn.commit()
            st.success(f"カラム '{column_name}' を削除しました")
            return True
        except Exception as e:
            st.error(f"カラム削除エラー: {str(e)}")
            return False

    def rename_column(self, table_name: str, old_name: str, new_name: str) -> bool:
        """既存テーブルのカラム名を変更（SQLite 3.25以降対応）"""
        try:
            sql = f"ALTER TABLE {table_name} RENAME COLUMN {old_name} TO {new_name}"
            self.cursor.execute(sql)
            self.conn.commit()
            st.success(f"カラム名を '{old_name}' から '{new_name}' に変更しました")
            return True
        except Exception as e:
            st.error(f"カラム名変更エラー: {str(e)}")
            return False

    def add_data(self, table_name: str, data: Dict) -> bool:
        """任意テーブルにデータを追加"""
        try:
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['?' for _ in data])
            values = tuple(data.values())
            query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
            self.cursor.execute(query, values)
            self.conn.commit()
            return True
        except Exception as e:
            st.error(f"データ追加エラー: {str(e)}")
            return False

    def update_data(self, table_name: str, row_id: int, data: Dict) -> bool:
        """任意テーブルのデータを更新"""
        try:
            set_clause = ', '.join([f"{key} = ?" for key in data.keys()])
            values = tuple(data.values()) + (row_id,)
            query = f"UPDATE {table_name} SET {set_clause} WHERE id = ?"
            self.cursor.execute(query, values)
            self.conn.commit()
            return True
        except Exception as e:
            st.error(f"データ更新エラー: {str(e)}")
            return False

    def delete_data(self, table_name: str, row_id: int) -> bool:
        """任意テーブルのデータを削除"""
        try:
            query = f"DELETE FROM {table_name} WHERE id = ?"
            self.cursor.execute(query, (row_id,))
            self.conn.commit()
            return True
        except Exception as e:
            st.error(f"データ削除エラー: {str(e)}")
            return False

    def search_data(self, table_name: str, search_term: str) -> pd.DataFrame:
        """任意テーブルで全カラム横断LIKE検索"""
        try:
            self.cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [row[1] for row in self.cursor.fetchall() if row[1] != 'id']
            like_clauses = [f"{col} LIKE ?" for col in columns]
            query = f"SELECT * FROM {table_name} WHERE {' OR '.join(like_clauses)}"
            params = [f"%{search_term}%"] * len(like_clauses)
            df = pd.read_sql_query(query, self.conn, params=params)
            return df
        except Exception as e:
            st.error(f"検索エラー: {str(e)}")
            return pd.DataFrame()

    def update_case_status_and_notes(self, case_id, user_status, admin_status, user_note, admin_note):
        try:
            query = """
                UPDATE cases
                SET user_status = ?, admin_status = ?, user_note = ?, admin_note = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """
            self.cursor.execute(query, (user_status, admin_status, user_note, admin_note, case_id))
            self.conn.commit()
            return True
        except Exception as e:
            st.error(f"案件ステータス・メモ更新エラー: {str(e)}")
            return False

def get_available_databases() -> List[str]:
    """利用可能なデータベースファイルのリストを取得"""
    os.makedirs(DB_DIR, exist_ok=True)
    db_files = glob.glob(os.path.join(DB_DIR, "*.db"))
    return [os.path.basename(db) for db in db_files]

def main():
    """メイン関数"""
    st.title("データベース管理ツール")
    
    # サイドバーに新しいデータベース作成セクションを追加
    st.sidebar.header("データベース操作")
    
    # 新しいデータベース作成
    new_db_name = st.sidebar.text_input("新しいデータベース名（.db拡張子付き）")
    new_db_type = st.sidebar.selectbox(
        "データベースの種類",
        ["案件データベース", "質問データベース", "カスタムデータベース"]
    )
    
    # Excelファイルからテーブルを作成するオプション
    if new_db_type == "カスタムデータベース":
        excel_file = st.sidebar.file_uploader("Excelファイルをアップロード", type=['xlsx'], key="create_db_excel")
        table_name = st.sidebar.text_input("テーブル名")
    
    if st.sidebar.button("新しいデータベースを作成"):
        if new_db_name:
            # dbディレクトリが存在しなければエラー
            if not os.path.isdir(DB_DIR):
                st.sidebar.error(f"データベースディレクトリ {DB_DIR} が存在しません。")
            else:
                db_filename = os.path.basename(new_db_name)
                new_db_name = os.path.join(DB_DIR, db_filename)
                db_manager = DBManager()
                if new_db_type == "カスタムデータベース":
                    if excel_file is not None and table_name:
                        if db_manager.create_new_database(new_db_name, new_db_type):
                            if db_manager.create_table_from_excel(excel_file, table_name):
                                st.sidebar.success(f"データベース '{new_db_name}' を作成し、テーブル '{table_name}' にデータをインポートしました")
                            else:
                                st.sidebar.error("テーブルの作成に失敗しました")
                    else:
                        st.sidebar.error("Excelファイルとテーブル名を指定してください")
                else:
                    if db_manager.create_new_database(new_db_name, new_db_type):
                        st.sidebar.success(f"データベース '{new_db_name}' を作成しました")
                    else:
                        st.sidebar.error("データベースの作成に失敗しました")
        else:
            st.sidebar.error("データベース名を入力してください")
    
    st.sidebar.divider()
    
    # 利用可能なデータベースのリストを取得
    available_dbs = get_available_databases()
    
    # データベース選択
    if not available_dbs:
        st.warning("利用可能なデータベースがありません。新規作成してください。")
        return

    selected_db = st.sidebar.selectbox(
        "操作するデータベースを選択",
        available_dbs
    )
    
    # データベースマネージャーの初期化
    db_path = os.path.join(DB_DIR, selected_db)
    db_manager = DBManager(db_path)
    if not db_manager.connect():
        return

    # データベースの種類を判定
    tables = db_manager.get_table_info()
    
    # データベース情報の表示
    st.subheader(f"データベース: {selected_db}")
    st.write(f"テーブル数: {len(tables)}")
    
    # 新しいテーブル作成フォーム
    st.subheader("新しいテーブルを作成")
    
    # カラム数の管理
    if 'num_columns' not in st.session_state:
        st.session_state.num_columns = 1
    
    # カラム数を増減するボタン（フォームの外）
    col1, col2 = st.columns(2)
    with col1:
        if st.button("カラムを追加", key="add_column"):
            st.session_state.num_columns += 1
            st.experimental_rerun()
    with col2:
        if st.session_state.num_columns > 1 and st.button("カラムを削除", key="remove_column"):
            st.session_state.num_columns -= 1
            st.experimental_rerun()
    
    # テーブル作成フォーム
    with st.form("create_table_form"):
        new_table_name = st.text_input("テーブル名")
        
        # カラム定義の入力
        st.write("カラム定義")
        
        # カラム定義の入力フォーム
        columns = []
        for i in range(st.session_state.num_columns):
            st.write(f"カラム {i+1}")
            col1, col2, col3 = st.columns(3)
            with col1:
                col_name = st.text_input(f"カラム名", key=f"col_name_{i}")
            with col2:
                col_type = st.selectbox(
                    f"データ型",
                    ["TEXT", "INTEGER", "REAL", "BLOB", "DATE"],
                    key=f"col_type_{i}"
                )
            with col3:
                col_constraints = st.multiselect(
                    f"制約",
                    ["NOT NULL", "UNIQUE", "DEFAULT ''"],
                    key=f"col_constraints_{i}"
                )
            
            if col_name:  # カラム名が入力されている場合のみ追加
                columns.append({
                    'name': col_name,
                    'type': col_type,
                    'constraints': ' '.join(col_constraints)
                })
        
        # フォームの送信ボタン
        submitted = st.form_submit_button("テーブルを作成")
        if submitted:
            if new_table_name and columns:
                if db_manager.create_table(new_table_name, columns):
                    st.session_state.num_columns = 1  # フォームをリセット
                    st.experimental_rerun()
            else:
                st.error("テーブル名と少なくとも1つのカラムを入力してください")
    
    # テーブル一覧の表示
    if tables:
        st.write("テーブル一覧:")
        for table in tables:
            with st.expander(f"テーブル: {table}"):
                # テーブル構造の表示
                st.write("テーブル構造:")
                structure_df = db_manager.get_table_structure(table)
                st.dataframe(structure_df)
                
                # --- カラム操作セクション ---
                st.markdown("---")
                st.subheader("カラム操作")
                col1, col2, col3 = st.columns(3)
                columns_list = structure_df['name'].tolist()
                # カラム追加フォーム
                with col1:
                    with st.form(f"add_col_form_{table}"):
                        st.markdown("**カラム追加**")
                        new_col_name = st.text_input("カラム名", key=f"add_col_name_{table}")
                        new_col_type = st.selectbox("データ型", ["TEXT", "INTEGER", "REAL", "BLOB", "DATE"], key=f"add_col_type_{table}")
                        new_col_constraints = st.multiselect("制約", ["NOT NULL", "UNIQUE", "DEFAULT ''"], key=f"add_col_constraints_{table}")
                        if st.form_submit_button("追加"):
                            if new_col_name:
                                constraints = ' '.join(new_col_constraints)
                                if db_manager.add_column(table, new_col_name, new_col_type, constraints):
                                    st.experimental_rerun()
                            else:
                                st.error("カラム名を入力してください")
                # カラム削除フォーム
                with col2:
                    with st.form(f"del_col_form_{table}"):
                        st.markdown("**カラム削除**")
                        del_col_name = st.selectbox("削除するカラム", columns_list, key=f"del_col_name_{table}")
                        if st.form_submit_button("削除"):
                            if del_col_name:
                                if db_manager.drop_column(table, del_col_name):
                                    st.experimental_rerun()
                            else:
                                st.error("削除するカラムを選択してください")
                # カラム名変更フォーム
                with col3:
                    with st.form(f"rename_col_form_{table}"):
                        st.markdown("**カラム名変更**")
                        old_col_name = st.selectbox("変更前カラム名", columns_list, key=f"old_col_name_{table}")
                        new_col_name2 = st.text_input("新しいカラム名", key=f"new_col_name2_{table}")
                        if st.form_submit_button("変更"):
                            if old_col_name and new_col_name2:
                                if db_manager.rename_column(table, old_col_name, new_col_name2):
                                    st.experimental_rerun()
                            else:
                                st.error("両方のカラム名を入力してください")
                st.markdown("---")
                # テーブルデータの表示
                st.write("テーブルデータ:")
                data_df = db_manager.get_table_data(table)
                st.dataframe(data_df)
                # テーブル削除ボタン
                if st.button(f"テーブル '{table}' を削除", key=f"delete_{table}"):
                    if db_manager.delete_table(table):
                        st.experimental_rerun()
    else:
        st.warning("データベースにテーブルが存在しません")

    if 'cases' in tables:
        db_type = "案件データベース"
    elif 'questions' in tables:
        db_type = "質問データベース"
    else:
        db_type = "カスタムデータベース"
        st.info(f"カスタムデータベース: {', '.join(tables)} テーブルが含まれています")

    # Excelファイルのアップロードとエクスポート
    st.sidebar.header("Excelファイル操作")
    
    # エクスポート
    if st.sidebar.button("データベースをExcelにエクスポート"):
        excel_data = db_manager.export_to_excel()
        if excel_data:
            st.sidebar.download_button(
                label="Excelファイルをダウンロード",
                data=excel_data,
                file_name=f"{selected_db}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    
    # インポート
    uploaded_file = st.sidebar.file_uploader("Excelファイルをアップロード", type=['xlsx'], key="import_excel")
    if uploaded_file is not None:
        if st.sidebar.button("データベースを更新"):
            if db_manager.import_from_excel(uploaded_file):
                st.sidebar.success("データベースを更新しました")
            else:
                st.sidebar.error("データベースの更新に失敗しました")

    # 操作の選択
    st.sidebar.header("操作を選択")
    operation = st.sidebar.selectbox(
        "実行する操作を選択",
        ["データの表示", "データの追加", "データの更新", "データの削除", "データの検索"]
    )

    if operation == "データの表示":
        # テーブル選択
        if tables:
            selected_table = st.selectbox("表示するテーブルを選択", tables)
            df = db_manager.get_table_data(selected_table)
            st.dataframe(df)
        else:
            st.warning("表示可能なテーブルがありません")

    elif operation == "データの追加":
        if tables:
            selected_table = st.selectbox("データを追加するテーブルを選択", tables)
            # テーブルの構造を取得
            structure_df = db_manager.get_table_structure(selected_table)
            # 入力フォームの作成
            with st.form("add_data_form"):
                data = {}
                for _, row in structure_df.iterrows():
                    if row['name'] != 'id':  # idは自動採番なので除外
                        col_name = row['name']
                        col_type = row['type']
                        if col_type == 'INTEGER':
                            data[col_name] = st.number_input(col_name, step=1)
                        elif col_type == 'REAL':
                            data[col_name] = st.number_input(col_name, step=0.1)
                        else:
                            data[col_name] = st.text_input(col_name)
                
                if st.form_submit_button("データを追加"):
                    if db_manager.add_data(selected_table, data):
                        st.success("データを追加しました")
                    else:
                        st.error("データの追加に失敗しました")
        else:
            st.warning("データを追加できるテーブルがありません")

    elif operation == "データの更新":
        if tables:
            selected_table = st.selectbox("データを更新するテーブルを選択", tables)
            # 更新対象のIDを選択
            df = db_manager.get_table_data(selected_table)
            if not df.empty:
                selected_id = st.selectbox("更新するデータのIDを選択", df['id'].tolist())
                # テーブルの構造を取得
                structure_df = db_manager.get_table_structure(selected_table)
                # 入力フォームの作成
                with st.form("update_data_form"):
                    data = {}
                    for _, row in structure_df.iterrows():
                        if row['name'] != 'id':  # idは更新しない
                            col_name = row['name']
                            col_type = row['type']
                            current_value = df[df['id'] == selected_id][col_name].iloc[0]
                            if col_type == 'INTEGER':
                                data[col_name] = st.number_input(col_name, value=current_value, step=1)
                            elif col_type == 'REAL':
                                data[col_name] = st.number_input(col_name, value=current_value, step=0.1)
                            else:
                                data[col_name] = st.text_input(col_name, value=str(current_value))
                    
                    if st.form_submit_button("データを更新"):
                        if db_manager.update_data(selected_table, selected_id, data):
                            st.success("データを更新しました")
                        else:
                            st.error("データの更新に失敗しました")
            else:
                st.warning("更新可能なデータがありません")
        else:
            st.warning("データを更新できるテーブルがありません")

    elif operation == "データの削除":
        if tables:
            selected_table = st.selectbox("データを削除するテーブルを選択", tables)
            # 削除対象のIDを選択
            df = db_manager.get_table_data(selected_table)
            if not df.empty:
                selected_id = st.selectbox("削除するデータのIDを選択", df['id'].tolist())
                if st.button("データを削除"):
                    if db_manager.delete_data(selected_table, selected_id):
                        st.success("データを削除しました")
                    else:
                        st.error("データの削除に失敗しました")
            else:
                st.warning("削除可能なデータがありません")
        else:
            st.warning("データを削除できるテーブルがありません")

    elif operation == "データの検索":
        if tables:
            selected_table = st.selectbox("検索するテーブルを選択", tables)
            search_term = st.text_input("検索キーワードを入力")
            if search_term:
                df = db_manager.search_data(selected_table, search_term)
                st.dataframe(df)
        else:
            st.warning("検索可能なテーブルがありません")

    db_manager.close()

if __name__ == "__main__":
    main() 