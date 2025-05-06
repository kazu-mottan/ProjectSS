import streamlit as st
from .database import DatabaseManager
import pandas as pd
from typing import Dict, Optional, List
import re
import json
import os
from datetime import datetime

class QAManager:
    """問診票（QA）管理クラス"""
    def __init__(self):
        self.db = DatabaseManager(db_path="db/qa.db")
    
    def save_case(self, name: str, transcription: str, diarization: str, 
                 categories: Dict, summary: str, date: datetime, notes: str):
        """案件を保存する"""
        case = {
            "company_name": name,
            "transcription": transcription,
            "diarization": diarization,
            "categories": categories,
            "summary": summary,
            "date": date.strftime("%Y-%m-%d"),
            "notes": notes,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.db.add_case(case)
    
    def get_cases(self) -> List[Dict]:
        """保存されている案件一覧を取得する"""
        df = self.db.get_all_cases()
        return df.to_dict(orient="records") if not df.empty else []
    
    def get_case_data(self, case_id: int) -> Dict:
        """案件データを取得する"""
        return self.db.get_case(case_id) or {}
    
    def update_case_data(self, case_id: int, case_data: Dict):
        """案件データを更新する"""
        return self.db.update_case(case_id, case_data)
    
    def delete_case_data(self, case_id: int):
        """案件データを削除する"""
        return self.db.delete_case(case_id)
    
    def add_case(self, **kwargs) -> Optional[int]:
        """案件を追加する"""
        case_data = {
            'company_name': kwargs.get('company_name', ''),
            'branch_number': kwargs.get('branch_number', ''),
            'cif_name': kwargs.get('cif_name', ''),
            'case_type': kwargs.get('case_type', ''),
            'fa_name': kwargs.get('responsible_fa', ''),
            'staff_name': kwargs.get('responsible_staff', ''),
            'audio_file': kwargs.get('audio_file', ''),
            'transcribed_text': kwargs.get('transcribed_text', ''),
            'diarized_text': kwargs.get('diarized_text', ''),
            'categories': kwargs.get('categories', '')
        }
        success = self.db.add_case(case_data)
        if success:
            # 追加した案件のIDを返す
            df = self.db.get_all_cases()
            if not df.empty:
                return df.iloc[-1]['id']
        return None
    
    def get_case(self, case_id: int) -> Optional[Dict]:
        """案件を取得する"""
        return self.db.get_case(case_id)
    
    def get_all_cases(self) -> List[Dict]:
        """全案件を取得する"""
        df = self.db.get_all_cases()
        return df.to_dict(orient="records") if not df.empty else []
    
    def display_case_form(self) -> Dict[str, str]:
        """案件登録フォームの表示"""
        st.subheader("案件情報登録")
        
        with st.form("case_form"):
            company_name = st.text_input("法人名")
            branch_number = st.text_input("店番")
            cif_name = st.text_input("CIF名")
            case_type = st.text_input("案件種別")
            fa_name = st.text_input("担当FA")
            staff_name = st.text_input("担当事務")
            
            submitted = st.form_submit_button("登録")
            
            if submitted:
                if all([company_name, branch_number, cif_name, case_type, fa_name, staff_name]):
                    case_data = {
                        'company_name': company_name,
                        'branch_number': branch_number,
                        'cif_name': cif_name,
                        'case_type': case_type,
                        'fa_name': fa_name,
                        'staff_name': staff_name
                    }
                    case_id = self.add_case(**case_data)
                    if case_id is not None:
                        st.success("案件を登録しました。")
                        return case_data
                else:
                    st.error("全ての項目を入力してください。")
        
        return {}
    
    def display_case_list(self):
        """案件一覧の表示と編集"""
        st.subheader("案件一覧")
        
        # 全案件の取得
        cases = self.get_all_cases()
        
        if cases:
            # 検索・フィルタリング
            self._display_search_filters(cases)
            
            # フィルタリングされたデータの取得
            filtered_cases = self._filter_cases(cases)
            
            if filtered_cases:
                # 編集モードの選択
                edit_mode = st.checkbox("編集モード")
                
                if edit_mode:
                    # 編集用のフォームを表示
                    self._display_edit_forms(filtered_cases)
                else:
                    # 通常の一覧表示
                    self._display_case_table(filtered_cases)
            else:
                st.info("検索条件に一致する案件はありません。")
        else:
            st.info("登録されている案件はありません。")
    
    def _display_search_filters(self, cases: List[Dict]):
        """検索・フィルタリングUIの表示"""
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.session_state.search_company = st.text_input(
                "法人名で検索",
                value=st.session_state.get('search_company', '')
            )
            st.session_state.search_branch = st.text_input(
                "店番で検索",
                value=st.session_state.get('search_branch', '')
            )
        
        with col2:
            st.session_state.search_cif = st.text_input(
                "CIF名で検索",
                value=st.session_state.get('search_cif', '')
            )
            st.session_state.search_type = st.text_input(
                "案件種別で検索",
                value=st.session_state.get('search_type', '')
            )
        
        with col3:
            st.session_state.search_fa = st.text_input(
                "担当FAで検索",
                value=st.session_state.get('search_fa', '')
            )
            st.session_state.search_staff = st.text_input(
                "担当事務で検索",
                value=st.session_state.get('search_staff', '')
            )
    
    def _filter_cases(self, cases: List[Dict]) -> List[Dict]:
        """案件のフィルタリング"""
        filtered_cases = cases.copy()
        
        # 各フィールドでのフィルタリング
        if st.session_state.get('search_company'):
            filtered_cases = [
                case for case in filtered_cases
                if st.session_state.search_company.lower() in case['company_name'].lower()
            ]
        
        if st.session_state.get('search_branch'):
            filtered_cases = [
                case for case in filtered_cases
                if st.session_state.search_branch.lower() in case['branch_number'].lower()
            ]
        
        if st.session_state.get('search_cif'):
            filtered_cases = [
                case for case in filtered_cases
                if st.session_state.search_cif.lower() in case['cif_name'].lower()
            ]
        
        if st.session_state.get('search_type'):
            filtered_cases = [
                case for case in filtered_cases
                if st.session_state.search_type.lower() in case['case_type'].lower()
            ]
        
        if st.session_state.get('search_fa'):
            filtered_cases = [
                case for case in filtered_cases
                if st.session_state.search_fa.lower() in case['fa_name'].lower()
            ]
        
        if st.session_state.get('search_staff'):
            filtered_cases = [
                case for case in filtered_cases
                if st.session_state.search_staff.lower() in case['staff_name'].lower()
            ]
        
        return filtered_cases
    
    def _display_case_table(self, cases: List[Dict]):
        """案件一覧の表示"""
        # 表示する列の選択
        display_columns = [
            'company_name', 'branch_number', 'cif_name',
            'case_type', 'fa_name', 'staff_name'
        ]
        
        # データフレームの作成
        df = pd.DataFrame(cases)
        if not df.empty:
            # データフレームの表示
            st.dataframe(
                df[display_columns],
                use_container_width=True,
                hide_index=True
            )
            
            # 案件選択
            selected_index = st.selectbox(
                "案件を選択",
                options=df.index,
                format_func=lambda x: f"{df.loc[x, 'company_name']} - {df.loc[x, 'cif_name']}"
            )
            
            if selected_index is not None:
                selected_case = df.loc[selected_index]
                st.session_state.selected_case = {
                    'id': selected_case['id'],
                    'company_name': selected_case['company_name'],
                    'branch_number': selected_case['branch_number'],
                    'cif_name': selected_case['cif_name'],
                    'case_type': selected_case['case_type'],
                    'fa_name': selected_case['fa_name'],
                    'staff_name': selected_case['staff_name']
                }
                
                # 選択された案件の詳細表示
                with st.expander("選択された案件の詳細"):
                    st.write(f"**法人名**: {selected_case['company_name']}")
                    st.write(f"**店番**: {selected_case['branch_number']}")
                    st.write(f"**CIF名**: {selected_case['cif_name']}")
                    st.write(f"**案件種別**: {selected_case['case_type']}")
                    st.write(f"**担当FA**: {selected_case['fa_name']}")
                    st.write(f"**担当事務**: {selected_case['staff_name']}")
    
    def _display_edit_forms(self, cases: List[Dict]):
        """編集フォームの表示"""
        for case in cases:
            with st.expander(f"案件: {case['company_name']} (ID: {case['id']})"):
                with st.form(f"edit_form_{case['id']}"):
                    company_name = st.text_input(
                        "法人名",
                        value=case['company_name'],
                        key=f"company_{case['id']}"
                    )
                    branch_number = st.text_input(
                        "店番",
                        value=case['branch_number'],
                        key=f"branch_{case['id']}"
                    )
                    cif_name = st.text_input(
                        "CIF名",
                        value=case['cif_name'],
                        key=f"cif_{case['id']}"
                    )
                    case_type = st.text_input(
                        "案件種別",
                        value=case['case_type'],
                        key=f"type_{case['id']}"
                    )
                    fa_name = st.text_input(
                        "担当FA",
                        value=case['fa_name'],
                        key=f"fa_{case['id']}"
                    )
                    staff_name = st.text_input(
                        "担当事務",
                        value=case['staff_name'],
                        key=f"staff_{case['id']}"
                    )
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.form_submit_button("更新"):
                            # 更新処理
                            updated_case = {
                                'id': case['id'],
                                'company_name': company_name,
                                'branch_number': branch_number,
                                'cif_name': cif_name,
                                'case_type': case_type,
                                'fa_name': fa_name,
                                'staff_name': staff_name
                            }
                            if self.update_case_data(case['id'], updated_case):
                                st.success("案件を更新しました。")
                            else:
                                st.error("案件の更新に失敗しました。")
                    with col2:
                        if st.form_submit_button("削除"):
                            if self.delete_case_data(case['id']):
                                st.success("案件を削除しました。")
                            else:
                                st.error("案件の削除に失敗しました。")

    def display_audio_upload(self):
        """音声アップロード画面の表示"""
        st.subheader("音声ファイルアップロード")
        audio_path = audio_capture.upload_audio()
        if audio_path:
            self.session_state.audio_path = audio_path
            st.success(f"音声ファイルを受け付けました: {audio_path}")
            
            # 音声処理の実行
            result = self.audio_processor.process_audio(audio_path)
            
            # 結果の表示
            if "text" in result:
                self.session_state.text = result["text"]
                st.subheader("音声認識結果")
                st.text_area("テキスト", value=result["text"], height=200)
            
            if "speakers" in result:
                self.session_state.separated_text = result["speakers"]
                st.subheader("話者分離結果")
                st.text_area("話者分離", value=result["speakers"], height=200)
            
            if "categories" in result:
                self.session_state.categories = result["categories"]
                self.categorizer.display_categories(result["categories"])
            
            # サマリー生成
            st.subheader("サマリー生成")
            if st.button("サマリーを生成"):
                with st.spinner("サマリーを生成中..."):
                    summary = self.audio_processor.generate_summary(result["text"])
                    if summary:
                        st.success("サマリーの生成が完了しました")
                        st.text_area("サマリー", value=summary, height=200)
                        
                        # 案件情報の入力フォーム
                        st.subheader("案件情報の入力")
                        case_data = self.display_case_form()
                        
                        if case_data:
                            # 音声処理結果とサマリーを案件情報に追加
                            case_data.update({
                                'audio_file': audio_path,
                                'transcribed_text': result["text"],
                                'diarized_text': result["speakers"],
                                'categories': result["categories"],
                                'summary': summary
                            })
                            
                            # 案件の追加
                            case_id = self.add_case(**case_data)
                            if case_id:
                                st.success(f"案件を登録しました（ID: {case_id}）")
                                st.session_state.case_id = case_id
                            else:
                                st.error("案件の登録に失敗しました")

    # 質問取得
    def get_questions(self) -> List[Dict]:
        df = self.db.get_table_data("question")
        return df.to_dict(orient="records") if not df.empty else []

    def get_question(self, question_id: int) -> Optional[Dict]:
        df = self.db.get_table_data("question")
        if not df.empty:
            row = df[df['id'] == question_id]
            if not row.empty:
                return row.iloc[0].to_dict()
        return None

    # 回答取得
    def get_answers(self) -> List[Dict]:
        df = self.db.get_table_data("answers")
        return df.to_dict(orient="records") if not df.empty else []

    def get_answer(self, answer_id: int) -> Optional[Dict]:
        df = self.db.get_table_data("answers")
        if not df.empty:
            row = df[df['id'] == answer_id]
            if not row.empty:
                return row.iloc[0].to_dict()
        return None

    # 回答追加
    def add_answer(self, answer_data: Dict) -> bool:
        return self.db.add_data("answers", answer_data)

    # 回答更新
    def update_answer(self, answer_id: int, answer_data: Dict) -> bool:
        return self.db.update_data("answers", answer_id, answer_data)

    # 回答削除
    def delete_answer(self, answer_id: int) -> bool:
        return self.db.delete_data("answers", answer_id) 