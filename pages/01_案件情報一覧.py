import streamlit as st
from modules.case_manager import QAManager
import pandas as pd
import sqlite3
import io

st.set_page_config(page_title="案件情報一覧", page_icon="📋")
st.title("案件情報一覧")

case_manager = QAManager()
cases = case_manager.get_cases()
if cases:
    df = pd.DataFrame(cases)
    edited_df = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        disabled=["id", "created_at", "updated_at"],
        key="cases_editor"
    )
    if st.button("保存（全件一括）"):
        for _, row in edited_df.iterrows():
            case_manager.update_case_all_fields(
                row["id"], row["company_name"], row["branch_number"], row["cif_name"],
                row["case_type"], row["fa_name"], row["staff_name"],
                row.get("user_status", ""), row.get("admin_status", ""),
                row.get("user_note", ""), row.get("admin_note", "")
            )
        st.success("全ての案件情報を更新しました")
        st.experimental_rerun()
    # --- 新規追加フォーム ---
    with st.expander("新規案件追加"):
        new_company_name = st.text_input("企業名（新規）")
        new_branch_number = st.text_input("拠点・支店番号（新規）")
        new_cif_name = st.text_input("顧客識別情報（新規）")
        new_case_type = st.text_input("案件種別（新規）")
        new_fa_name = st.text_input("担当FA（新規）")
        new_staff_name = st.text_input("担当者（新規）")
        new_user_status = st.text_input("ユーザーステータス（新規）")
        new_admin_status = st.text_input("管理者ステータス（新規）")
        new_user_note = st.text_area("ユーザーメモ（新規）")
        new_admin_note = st.text_area("管理者メモ（新規）")
        if st.button("追加"):
            case_manager.add_case(
                company_name=new_company_name,
                branch_number=new_branch_number,
                cif_name=new_cif_name,
                case_type=new_case_type,
                fa_name=new_fa_name,
                staff_name=new_staff_name,
                user_status=new_user_status,
                admin_status=new_admin_status,
                user_note=new_user_note,
                admin_note=new_admin_note
            )
            st.success("新規案件を追加しました")
            st.experimental_rerun()
    # --- エクスポート機能 ---
    st.markdown("---")
    st.subheader("案件データのエクスポート")
    export_format = st.selectbox("エクスポート形式", ["CSV", "Excel"])
    if st.button("エクスポート"):
        if export_format == "CSV":
            csv = df.to_csv(index=False).encode("utf-8-sig")
            st.download_button("CSVダウンロード", data=csv, file_name="案件一覧.csv", mime="text/csv")
        else:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name="案件一覧")
            st.download_button("Excelダウンロード", data=output.getvalue(), file_name="案件一覧.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
else:
    st.info("保存された案件はありません。") 