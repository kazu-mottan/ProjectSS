import streamlit as st
from modules.claude_vision_reader import ClaudeVisionReader
import sqlite3
import statistics
import google.generativeai as genai
from pdf2image import convert_from_path
import pandas as pd
from collections import Counter
import matplotlib.pyplot as plt
import numpy as np
import json
import re

st.set_page_config(page_title="画像読み取りAI（3ステップ版）", page_icon="🖼️")
st.title("画像読み取りAI（3ステップ版）")

# ページ幅拡張
st.markdown(
    """
    <style>
    .main .block-container { max-width: 1800px !important; }
    </style>
    """,
    unsafe_allow_html=True
)

db_path = "db/qa.db"
png_dir = "png"
reader = ClaudeVisionReader()

COMMON_PROMPT_TEMPLATE = """
画像内のテキストと数値を正確に読み取り、次の点に留意して、以下のすべての項目を抽出してください: {variables}
元のレイアウト・表形式をできるだけ保持してください（行・列の対応関係が分かるように）。
「0（ゼロ）」と「O（オー）」、「1（イチ）」と「I（アイ）」など、誤認識されやすい文字に注意してください。
「,」「.」「円」などの通貨や桁区切りの記号も正確に認識してください。
数値は半角で、単位（例：千円、百万円）はそのまま記載してください。
結果は JSON 形式で {変数名: 抽出内容} の形にしてください。解説は不要です。
"""

def gemini_ocr(file_path, prompt):
    api_key = st.secrets["gemini_api_key"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash")
    ext = file_path.split('.')[-1].lower()
    if ext == "pdf":
        images = convert_from_path(file_path)
        results = []
        for i, img in enumerate(images):
            buf = st.BytesIO()
            img.save(buf, format="PNG")
            image_data = buf.getvalue()
            response = model.generate_content([
                prompt + f"（{i+1}ページ目）",
                {"mime_type": "image/png", "data": image_data}
            ])
            results.append(response.text)
        return "\n".join(results)
    else:
        with open(file_path, "rb") as f:
            image_data = f.read()
        response = model.generate_content([
            prompt,
            {"mime_type": "image/png", "data": image_data}
        ])
        return response.text

# --- OCR実行対象を選択（テスト実行用） ---
st.header("[テスト用] OCR実行対象を選択・実行")
entries = reader.get_ocr_entries_with_images(db_path, png_dir)
if 'ocr_done' not in st.session_state:
    st.session_state.ocr_done = False

if not st.session_state.ocr_done:
    st.info("OCR実行対象を選択してください。選択したファイルごとに画像（左）とOCR操作（右）が表示されます。")
    entry_options = [f"ID:{e['id']} | {e['filename']}" for e in entries]
    selected_options_test = st.multiselect("OCR実行対象を選択（テスト用）", entry_options, key="ocr_entry_multiselect_test")
    selected_ids_test = [int(opt.split('|')[0].replace('ID:', '').strip()) for opt in selected_options_test]

    for entry in entries:
        if entry['id'] in selected_ids_test:
            with st.container():
                st.markdown(f"<div style='border:1px solid #ddd; border-radius:8px; padding:16px; margin-bottom:16px; background:#fafbfc'>", unsafe_allow_html=True)
                col_img, col_ocr = st.columns([7, 3], gap="large")
                with col_img:
                    st.markdown(f"#### プレビュー: {entry['filename']}")
                    if entry['type'] == "image":
                        st.image(entry['file_path'], caption=entry['filename'], width=350)
                    elif entry['type'] == "pdf":
                        st.markdown(f"[PDFを開く]({entry['file_path']})")
                    else:
                        st.info("対応していないファイル形式です。")
                with col_ocr:
                    st.markdown(f"**want_to_read:** {entry['want_to_read']}")
                    key_claude = f"claude_result_test_{entry['id']}"
                    key_openai = f"openai_result_test_{entry['id']}"
                    if st.button(f"ClaudeでOCR実行（テスト）", key=f"claude_ocr_test_{entry['id']}"):
                        common_prompt = COMMON_PROMPT_TEMPLATE.replace("{variables}", entry['want_to_read'])
                        result = reader.read_image_and_extract_info(entry['file_path'], common_prompt)
                        st.session_state[key_claude] = result
                    if key_claude in st.session_state:
                        st.success(f"Claude Vision（{reader.model}）OCR結果（生出力）:\n{st.session_state[key_claude]}")
                    if st.button(f"OpenAIでOCR実行（テスト）", key=f"openai_ocr_test_{entry['id']}"):
                        prompt = reader.make_ocr_prompt(entry['want_to_read'])
                        result = reader.openai_read_image_and_extract_info(entry['file_path'], prompt)
                        st.session_state[key_openai] = result
                    if key_openai in st.session_state:
                        st.info(f"OpenAI Vision（gpt-4o）OCR結果:\n{st.session_state[key_openai]}")
                    if (key_claude in st.session_state or key_openai in st.session_state):
                        if st.button(f"出力結果を登録（このファイル）", key=f"register_result_test_{entry['id']}"):
                            conn = sqlite3.connect(db_path)
                            cursor = conn.cursor()
                            result_to_save = st.session_state.get(key_claude) or st.session_state.get(key_openai)
                            cursor.execute("UPDATE ocr SET result = ? WHERE id = ?", (result_to_save, entry['id']))
                            conn.commit()
                            conn.close()
                            st.success("出力結果をデータベースに登録しました。")
                st.markdown("</div>", unsafe_allow_html=True)
    run_ocr_test = st.button("選択したものだけOCR読み取りを実行（テスト用）", key="run_ocr_test")
    if run_ocr_test and selected_ids_test:
        with st.spinner("画像から情報を抽出中..."):
            for entry in entries:
                if entry['id'] in selected_ids_test:
                    key_claude = f"claude_result_test_{entry['id']}"
                    key_openai = f"openai_result_test_{entry['id']}"
                    common_prompt = COMMON_PROMPT_TEMPLATE.replace("{variables}", entry['want_to_read'])
                    result = reader.read_image_and_extract_info(entry['file_path'], common_prompt)
                    st.session_state[key_claude] = result
                    prompt = reader.make_ocr_prompt(entry['want_to_read'])
                    result_openai = reader.openai_read_image_and_extract_info(entry['file_path'], prompt)
                    st.session_state[key_openai] = result_openai
            st.session_state.ocr_done = True
            st.session_state.ocr_ids = selected_ids_test
            st.experimental_rerun()
    elif run_ocr_test and not selected_ids_test:
        st.warning("OCR実行対象を1つ以上選択してください。")
# else: ここではst.multiselectを絶対に呼ばない

# --- 1. ファイルアップロード ---
st.header("STEP 1: 画像またはPDFをアップロード")
uploaded_file = st.file_uploader("画像またはPDFを選択", type=["png", "jpg", "jpeg", "pdf"], accept_multiple_files=False)

if uploaded_file:
    st.success("ファイルがアップロードされました。次に進んでください。")
    # 一時保存
    file_ext = uploaded_file.name.split('.')[-1].lower()
    file_type = "image" if file_ext in ["png", "jpg", "jpeg"] else "pdf"
    save_path = f"tmp_{uploaded_file.name}"
    with open(save_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    # プレビュー
    if file_type == "image":
        st.image(save_path, caption=uploaded_file.name, width=350)
    else:
        st.markdown(f"[PDFを開く]({save_path})")

    # --- 2. AIで全情報をテーブル化（各AIモデルで比較） ---
    st.header("STEP 2: AIで画像内の全情報をテーブル化（各AIモデルで比較）")
    # Settings.jsonから複数プロンプトを読み込む
    prompt_dict = {}
    try:
        with open("Settings.json", "r", encoding="utf-8") as f:
            settings = json.load(f)
            prompt_dict = settings.get("prompts", {})
    except Exception:
        prompt_dict = {}
    prompt_options = ["（自由入力）"] + list(prompt_dict.keys())
    selected_prompt = st.selectbox("プロンプト選択", prompt_options, index=0)
    if selected_prompt != "（自由入力）" and selected_prompt in prompt_dict:
        default_prompt = prompt_dict[selected_prompt]
    else:
        default_prompt = ""
    custom_prompt = st.text_area(
        "テーブル化プロンプト（任意。空欄の場合はデフォルトプロンプトを使用）",
        value=default_prompt,
        placeholder="例: 画像内の全ての情報を表形式（JSON: {\"columns\": [...], \"data\": [[...], ...]}}）で出力してください..."
    )
    if st.button("AIでテーブル化（全モデル比較）", key="tableize_all") or st.session_state.get("table_json_all"):
        with st.spinner("AIが画像から全情報をテーブル化しています（全モデル）..."):
            if custom_prompt.strip():
                table_prompt = custom_prompt.strip()
            else:
                table_prompt = (
                    f"あなたは優秀な企業アナリストです。画像内の全ての情報を表形式（JSON: {{\"columns\": [...], \"data\": [[...], ...]}}）で出力してください。"
                    "絶対にJSONだけを返してください。解説や余計な文章は不要です。"
                    "テーブル内の空白セルも正確に抽出し、空欄は空文字列（\"\"）で出力してください。"
                )
            model_results = {}
            # Claude
            try:
                claude_result = reader.read_image_and_extract_info(save_path, table_prompt)
                match = re.search(r'\{[\s\S]*\}', claude_result)
                if match:
                    claude_json = json.loads(match.group())
                    model_results['Claude'] = claude_json
                    st.session_state["table_json"] = claude_json
                else:
                    model_results['Claude'] = None
            except Exception as e:
                model_results['Claude'] = None
                st.error(f"Claude Visionの出力パース失敗: {e}")
            # OpenAI
            try:
                openai_result = reader.openai_read_image_and_extract_info(save_path, table_prompt)
                match = re.search(r'\{[\s\S]*\}', openai_result)
                if match:
                    openai_json = json.loads(match.group())
                    model_results['OpenAI'] = openai_json
                else:
                    model_results['OpenAI'] = None
            except Exception as e:
                model_results['OpenAI'] = None
                st.error(f"OpenAI Visionの出力パース失敗: {e}")
            # Gemini
            try:
                gemini_result = gemini_ocr(save_path, table_prompt)
                match = re.search(r'\{[\s\S]*\}', gemini_result)
                if match:
                    gemini_json = json.loads(match.group())
                    model_results['Gemini'] = gemini_json
                else:
                    model_results['Gemini'] = None
            except Exception as e:
                model_results['Gemini'] = None
                st.error(f"Geminiの出力パース失敗: {e}")
            st.session_state["table_json_all"] = model_results
            st.success("各AIモデルのテーブル化出力を比較します。")
            cols = st.columns(len(model_results))
            for i, (model, data) in enumerate(model_results.items()):
                with cols[i]:
                    st.subheader(model)
                    if data:
                        col_len = len(data["columns"])
                        bad_rows = [row for row in data["data"] if len(row) != col_len]
                        if bad_rows:
                            st.warning(f"カラム数とデータ数が一致しない行があります。AI出力を確認してください。")
                            st.write("columns:", data["columns"])
                            st.write("data:", data["data"])
                            if model == 'Claude':
                                st.write(claude_result)
                        try:
                            df = pd.DataFrame(
                                [row for row in data["data"] if len(row) == col_len],
                                columns=data["columns"]
                            )
                            st.dataframe(df, use_container_width=True)
                        except Exception as e:
                            st.error(f"DataFrame生成エラー: {e}")
                            st.write("columns:", data["columns"])
                            st.write("data:", data["data"])
                    else:
                        st.warning("テーブルデータを抽出できませんでした。生出力を下記に表示します。")
                        if model == 'Claude':
                            st.write(claude_result)

    # --- 3. 抽出条件入力・AIでフィルタリング ---
    if st.session_state.get("table_json"):
        st.header("STEP 3: テーブルから抽出したい条件や項目を入力（再学習イメージ）")
        filter_query = st.text_input("抽出したい条件やキーワードを入力（例: '売上が1000万円以上の行'、'日付が2024年のデータ' など）")
        extract_items_step3 = st.text_input("抽出したい項目（カンマ区切りで複数指定可。例: 氏名, 金額, 日付 など）", key="extract_items_step3")
        if st.button("AIで条件抽出", key="filter"):
            with st.spinner("AIが条件に合うデータを抽出しています..."):
                table_json = st.session_state["table_json"]
                extract_part = f"抽出したい項目: {extract_items_step3}。" if extract_items_step3 else ""
                filter_prompt = (
                    "次のテーブルデータ（JSON: {columns: [...], data: [[...], ...]}）から、" +
                    f"'{filter_query}' に合致する行だけを抽出し、同じ形式のJSONで返してください。絶対にJSONだけを返してください。解説や余計な文章は不要です。"
                    "テーブル内の空白セルも正確に抽出し、空欄は空文字列（\"\"）で出力してください。"
                    f"{extract_part}\n"
                    f"テーブルデータ: {json.dumps(table_json, ensure_ascii=False)}"
                )
                filter_result = reader.read_image_and_extract_info(save_path, filter_prompt)
                try:
                    json_start = filter_result.find('{')
                    json_str = filter_result[json_start:]
                    filtered_json = json.loads(json_str)
                    st.success("抽出結果を下記に表示します。")
                    df_filtered = pd.DataFrame(filtered_json["data"], columns=filtered_json["columns"])
                    st.dataframe(df_filtered, use_container_width=True)
                except Exception as e:
                    st.error(f"AIの出力から抽出結果を取得できませんでした: {e}")
                    st.write("AIの生出力:", filter_result)

    # 保存済み結果表示
    ocr_ids = st.session_state.get("ocr_ids", [])
    if st.session_state.get("ocr_done") and ocr_ids:
        st.success("選択した自社株のOCR読み取りが完了しました。下記に結果を表示します。")
        entries = reader.get_ocr_entries_with_images(db_path, png_dir)
        table_data = []
        for entry in entries:
            if entry['id'] in ocr_ids:
                key_claude = f"claude_result_{entry['id']}"
                key_openai = f"openai_result_{entry['id']}"
                table_data.append({
                    "ファイル名": entry['filename'],
                    "want_to_read": entry['want_to_read'],
                    f"Claude Vision（{reader.model}）": st.session_state.get(key_claude, ""),
                    "OpenAI Vision（gpt-4o）": st.session_state.get(key_openai, "")
                })
        if table_data:
            st.dataframe(table_data)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("もう一度選択・実行する", key="reset_ocr"):
                st.session_state.ocr_done = False
                st.session_state.ocr_ids = []
                st.experimental_rerun()
        with col2:
            if st.button("出力結果を一括登録", key="register_all_results"):
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                updated = 0
                for entry in entries:
                    if entry['id'] in ocr_ids:
                        key_claude = f"claude_result_{entry['id']}"
                        key_openai = f"openai_result_{entry['id']}"
                        result_to_save = st.session_state.get(key_claude) or st.session_state.get(key_openai)
                        if result_to_save:
                            cursor.execute("UPDATE ocr SET result = ? WHERE id = ?", (result_to_save, entry['id']))
                            updated += 1
                conn.commit()
                conn.close()
                st.success(f"{updated}件の出力結果をデータベースに登録しました。") 