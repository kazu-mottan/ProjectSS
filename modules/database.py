import sqlite3
import streamlit as st
from typing import List, Dict, Optional
import pandas as pd
import os

class DatabaseManager:
    """データベース管理クラス"""
    def __init__(self, db_path: str = "cases.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """データベースの初期化"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_name TEXT NOT NULL,
                    branch_number TEXT NOT NULL,
                    cif_name TEXT NOT NULL,
                    case_type TEXT NOT NULL,
                    fa_name TEXT NOT NULL,
                    staff_name TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
    
    def add_case(self, case_data: Dict[str, str]) -> bool:
        """案件の追加"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO cases (
                        company_name, branch_number, cif_name,
                        case_type, fa_name, staff_name
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    case_data['company_name'],
                    case_data['branch_number'],
                    case_data['cif_name'],
                    case_data['case_type'],
                    case_data['fa_name'],
                    case_data['staff_name']
                ))
                conn.commit()
            return True
        except Exception as e:
            st.error(f"案件の追加中にエラーが発生しました: {str(e)}")
            return False
    
    def update_case(self, case_id: int, case_data: Dict[str, str]) -> bool:
        """案件の更新"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE cases SET
                        company_name = ?,
                        branch_number = ?,
                        cif_name = ?,
                        case_type = ?,
                        fa_name = ?,
                        staff_name = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    case_data['company_name'],
                    case_data['branch_number'],
                    case_data['cif_name'],
                    case_data['case_type'],
                    case_data['fa_name'],
                    case_data['staff_name'],
                    case_id
                ))
                conn.commit()
            return True
        except Exception as e:
            st.error(f"案件の更新中にエラーが発生しました: {str(e)}")
            return False
    
    def delete_case(self, case_id: int) -> bool:
        """案件の削除"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM cases WHERE id = ?", (case_id,))
                conn.commit()
            return True
        except Exception as e:
            st.error(f"案件の削除中にエラーが発生しました: {str(e)}")
            return False
    
    def get_all_cases(self) -> pd.DataFrame:
        """全案件の取得"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                return pd.read_sql_query("""
                    SELECT 
                        id, company_name, branch_number, cif_name,
                        case_type, fa_name, staff_name,
                        created_at, updated_at
                    FROM cases
                    ORDER BY updated_at DESC
                """, conn)
        except Exception as e:
            st.error(f"案件の取得中にエラーが発生しました: {str(e)}")
            return pd.DataFrame()
    
    def get_case(self, case_id: int) -> Optional[Dict[str, str]]:
        """特定の案件の取得"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM cases WHERE id = ?
                """, (case_id,))
                row = cursor.fetchone()
                if row:
                    return {
                        'id': row[0],
                        'company_name': row[1],
                        'branch_number': row[2],
                        'cif_name': row[3],
                        'case_type': row[4],
                        'fa_name': row[5],
                        'staff_name': row[6]
                    }
                return None
        except Exception as e:
            st.error(f"案件の取得中にエラーが発生しました: {str(e)}")
            return None 