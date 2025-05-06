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
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from msrest.authentication import CognitiveServicesCredentials

st.set_page_config(page_title="読み取り機能(テスト版)", page_icon="🖼️")
st.title("読み取り機能(テスト版)")

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

def azure_ocr(file_path, prompt=None, want_to_read=None):
    """Azure Computer Vision OCR（画像・PDF両対応、キーワード抽出対応）"""
    import os
    endpoint = st.secrets["azure_vision_endpoint"]
    key = st.secrets["azure_vision_key"]
    client = ComputerVisionClient(endpoint, CognitiveServicesCredentials(key))
    ext = os.path.splitext(file_path)[1].lower()
    results = []
    if ext == ".pdf":
        images = convert_from_path(file_path)
        for i, img in enumerate(images):
            tmp_img_path = f"tmp_azure_{i}.png"
            img.save(tmp_img_path, format="PNG")
            with open(tmp_img_path, "rb") as f:
                ocr_result = client.recognize_printed_text_in_stream(image=f, language="ja")
            lines = []
            for region in ocr_result.regions:
                for line in region.lines:
                    lines.append("".join([w.text for w in line.words]))
            results.append("\n".join(lines))
            os.remove(tmp_img_path)
        text = "\n".join(results)
    else:
        with open(file_path, "rb") as f:
            ocr_result = client.recognize_printed_text_in_stream(image=f, language="ja")
        lines = []
        for region in ocr_result.regions:
            for line in region.lines:
                lines.append("".join([w.text for w in line.words]))
        text = "\n".join(lines)
    # --- キーワード抽出処理 ---
    if want_to_read:
        keywords = [w.strip() for w in want_to_read.split(",") if w.strip()]
        filtered = []
        for line in text.splitlines():
            if any(kw in line for kw in keywords):
                filtered.append(line)
        return "\n".join(filtered) if filtered else "(該当する行がありません)"
    else:
        return text

# --- 1. 複数ファイルアップロード ---
st.subheader("1. ファイルをアップロード（複数可）")
uploaded_files = st.file_uploader("画像またはPDFを選択", type=["png", "jpg", "jpeg", "pdf"], accept_multiple_files=True)

# --- 2. 各AIでOCR実行 ---
if uploaded_files:
    st.subheader("2. 各AIで読み取りを実行")
    want_to_read = st.text_input("読み取りたい項目（全ファイル共通）")
    for uploaded_file in uploaded_files:
        st.markdown(f"---\n#### ファイル: {uploaded_file.name}")
        # 一時保存
        file_ext = uploaded_file.name.split('.')[-1].lower()
        file_type = "image" if file_ext in ["png", "jpg", "jpeg"] else "pdf"
        save_path = f"tmp_{uploaded_file.name}"
        with open(save_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        # プレビュー
        col_img, col_ocr = st.columns([7, 3], gap="large")
        with col_img:
            if file_type == "image":
                st.image(save_path, caption=uploaded_file.name, width=350)
            elif file_type == "pdf":
                st.markdown(f"[PDFを開く]({save_path})")
        with col_ocr:
            # ファイルごとにwant_to_read入力欄
            want_to_read_file = st.text_input("読み取りたい項目（このファイル用）", value=want_to_read, key=f"want_to_read_{uploaded_file.name}")
            # 共通プロンプト生成
            common_prompt = COMMON_PROMPT_TEMPLATE.replace("{variables}", want_to_read_file)
            prompt = common_prompt

            # --- モデル選択・実行回数指定 ---
            model_options = ["Claude", "OpenAI", "Gemini", "Azure"]
            selected_models = st.multiselect("実行するAIモデル", model_options, default=["Claude", "OpenAI", "Gemini"])
            repeat = st.number_input("各モデルの実行回数", min_value=1, max_value=10, value=1, step=1, key=f"repeat_{uploaded_file.name}")
            task_type = st.selectbox("タスク種別（バギング用）", ["分類", "回帰"], key=f"task_type_{uploaded_file.name}")

            # --- 一括実行ボタン ---
            if st.button(f"選択したモデルで一括実行: {uploaded_file.name}", key=f"multi_run_{uploaded_file.name}"):
                all_results = {model: [] for model in selected_models}
                for model in selected_models:
                    for i in range(int(repeat)):
                        if model == "Claude":
                            result = reader.ocr_and_refine(save_path, prompt)
                        elif model == "OpenAI":
                            result = reader.openai_read_image_and_extract_info(save_path, prompt)
                        elif model == "Gemini":
                            result = gemini_ocr(save_path, prompt)
                        elif model == "Azure":
                            result = azure_ocr(save_path, prompt, want_to_read_file)
                        else:
                            result = ""
                        print(f"[{model} OCR result for {save_path} (run {i+1})]:\n{result}")
                        all_results[model].append(result)
                st.session_state[f"all_results_{uploaded_file.name}"] = all_results

        # --- 結果表示・バギング集計（中央寄せ） ---
        if f"all_results_{uploaded_file.name}" in st.session_state:
            all_results = st.session_state[f"all_results_{uploaded_file.name}"]
            # テーブル用データ作成
            table_data = []
            for i in range(int(repeat)):
                row = {"回数": i+1}
                for model in selected_models:
                    row[model] = all_results[model][i] if len(all_results[model]) > i else ""
                table_data.append(row)
            df = pd.DataFrame(table_data)
            st.markdown("<div style='text-align:center'><h4>各モデルの実行結果（全回）</h4></div>", unsafe_allow_html=True)
            st.dataframe(df, use_container_width=True)
            # バギング集計
            bagging_preds = []
            for i in range(int(repeat)):
                preds = [all_results[model][i] for model in selected_models if len(all_results[model]) > i]
                if not preds:
                    continue
                if task_type == "分類":
                    try:
                        bagging_pred = statistics.mode(preds)
                    except Exception:
                        bagging_pred = "-"
                else:
                    try:
                        nums = [float(p) for p in preds]
                        bagging_pred = sum(nums) / len(nums)
                    except Exception:
                        bagging_pred = "-"
                bagging_preds.append(bagging_pred)
            st.markdown("<div style='text-align:center'><h4>バギングによる最終予測（各回）</h4></div>", unsafe_allow_html=True)
            st.dataframe(pd.DataFrame({"回数": list(range(1, len(bagging_preds)+1)), "バギング予測": bagging_preds}), use_container_width=True)
            # グラフ表示
            if task_type == "分類":
                counter = Counter(bagging_preds)
                df_bar = pd.DataFrame(counter.items(), columns=["予測ラベル", "回数"])
                st.bar_chart(df_bar.set_index("予測ラベル"))
            else:
                fig, ax = plt.subplots()
                ax.hist([float(x) for x in bagging_preds if x != "-"], bins=10)
                ax.set_xlabel("予測値")
                ax.set_ylabel("頻度")
                st.pyplot(fig)

# 既存OCRエントリ表示・実行
entries = reader.get_ocr_entries_with_images(db_path, png_dir)
if 'ocr_done' not in st.session_state:
    st.session_state.ocr_done = False
if not st.session_state.ocr_done:
    st.info("OCR実行対象を選択してください。選択したファイルごとに画像（左）とOCR操作（右）が表示されます。")
    entry_options = [f"ID:{e['id']} | {e['filename']}" for e in entries]
    selected_options = st.multiselect("OCR実行対象を選択", entry_options)
    selected_ids = [int(opt.split('|')[0].replace('ID:', '').strip()) for opt in selected_options]

    for entry in entries:
        if entry['id'] in selected_ids:
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
                key_claude = f"claude_result_{entry['id']}"
                key_openai = f"openai_result_{entry['id']}"
                if st.button(f"ClaudeでOCR実行", key=f"claude_ocr_{entry['id']}"):
                    # Claudeも共通プロンプトを使う
                    common_prompt = COMMON_PROMPT_TEMPLATE.replace("{variables}", entry['want_to_read'])
                    result = reader.ocr_and_refine(entry['file_path'], common_prompt)
                    print(f"[Claude OCR result for {entry['file_path']}]:\n{result}")
                    st.session_state[key_claude] = result
                if key_claude in st.session_state:
                    st.success(f"Claude Vision（{reader.model}）OCR結果（整形済み）:\n{st.session_state[key_claude]}")
                if st.button(f"OpenAIでOCR実行", key=f"openai_ocr_{entry['id']}"):
                    prompt = reader.make_ocr_prompt(entry['want_to_read'])
                    result = reader.openai_read_image_and_extract_info(entry['file_path'], prompt)
                    st.session_state[key_openai] = result
                if key_openai in st.session_state:
                    st.info(f"OpenAI Vision（gpt-4o）OCR結果:\n{st.session_state[key_openai]}")
                # 出力結果をDBに登録するボタン
                if (key_claude in st.session_state or key_openai in st.session_state):
                    if st.button(f"出力結果を登録（このファイル）", key=f"register_result_{entry['id']}"):
                        conn = sqlite3.connect(db_path)
                        cursor = conn.cursor()
                        # Claude優先、なければOpenAI
                        result_to_save = st.session_state.get(key_claude) or st.session_state.get(key_openai)
                        cursor.execute("UPDATE ocr SET result = ? WHERE id = ?", (result_to_save, entry['id']))
                        conn.commit()
                        conn.close()
                        st.success("出力結果をデータベースに登録しました。")
    run_ocr = st.button("選択したものだけOCR読み取りを実行", key="run_ocr")
    if run_ocr and selected_ids:
        with st.spinner("画像から情報を抽出中..."):
            for entry in entries:
                if entry['id'] in selected_ids:
                    key_claude = f"claude_result_{entry['id']}"
                    key_openai = f"openai_result_{entry['id']}"
                    # Claudeも共通プロンプトを使う
                    common_prompt = COMMON_PROMPT_TEMPLATE.replace("{variables}", entry['want_to_read'])
                    result = reader.ocr_and_refine(entry['file_path'], common_prompt)
                    print(f"[Claude OCR result for {entry['file_path']}]:\n{result}")
                    st.session_state[key_claude] = result
                    # OpenAI
                    prompt = reader.make_ocr_prompt(entry['want_to_read'])
                    result_openai = reader.openai_read_image_and_extract_info(entry['file_path'], prompt)
                    print(f"[OpenAI OCR result for {entry['file_path']}]:\n{result_openai}")
                    st.session_state[key_openai] = result_openai
            st.session_state.ocr_done = True
            st.session_state.ocr_ids = selected_ids
            st.experimental_rerun()
    elif run_ocr and not selected_ids:
        st.warning("OCR実行対象を1つ以上選択してください。")
else:
    st.success("選択した自社株のOCR読み取りが完了しました。下記に結果を表示します。")
    entries = reader.get_ocr_entries_with_images(db_path, png_dir)
    # テーブル用データ作成
    table_data = []
    for entry in entries:
        if entry['id'] in st.session_state.ocr_ids:
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
                if entry['id'] in st.session_state.ocr_ids:
                    key_claude = f"claude_result_{entry['id']}"
                    key_openai = f"openai_result_{entry['id']}"
                    result_to_save = st.session_state.get(key_claude) or st.session_state.get(key_openai)
                    if result_to_save:
                        cursor.execute("UPDATE ocr SET result = ? WHERE id = ?", (result_to_save, entry['id']))
                        updated += 1
            conn.commit()
            conn.close()
            st.success(f"{updated}件の出力結果をデータベースに登録しました。") 