from .database import DatabaseManager
import streamlit as st

def init_sample_data():
    """サンプルデータの初期化"""
    db = DatabaseManager()
    
    # サンプルデータ
    sample_cases = [
        {
            'company_name': '株式会社ABC',
            'branch_number': '001',
            'cif_name': '山田太郎',
            'case_type': '融資',
            'fa_name': '佐藤一郎',
            'staff_name': '鈴木花子'
        },
        {
            'company_name': 'XYZ株式会社',
            'branch_number': '002',
            'cif_name': '田中次郎',
            'case_type': '投資',
            'fa_name': '高橋三郎',
            'staff_name': '伊藤美咲'
        },
        {
            'company_name': '株式会社DEF',
            'branch_number': '003',
            'cif_name': '中村四郎',
            'case_type': '保険',
            'fa_name': '渡辺五郎',
            'staff_name': '小林優子'
        },
        {
            'company_name': 'GHI株式会社',
            'branch_number': '004',
            'cif_name': '加藤六郎',
            'case_type': '相続',
            'fa_name': '山本七郎',
            'staff_name': '佐々木真理'
        },
        {
            'company_name': '株式会社JKL',
            'branch_number': '005',
            'cif_name': '木村八郎',
            'case_type': '資産運用',
            'fa_name': '清水九郎',
            'staff_name': '斎藤恵'
        }
    ]
    
    # データの追加
    for case in sample_cases:
        if db.add_case(case):
            st.success(f"サンプルデータを追加しました: {case['company_name']}")
        else:
            st.error(f"サンプルデータの追加に失敗しました: {case['company_name']}")

if __name__ == "__main__":
    st.title("サンプルデータ初期化")
    if st.button("サンプルデータを追加"):
        init_sample_data() 