import streamlit as st
from pdf2image import convert_from_path
import os
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from msrest.authentication import CognitiveServicesCredentials
import pandas as pd
import json

st.set_page_config(page_title="Azure OCR専用ページ", page_icon="🟦")
st.title("Azure OCR（画像・PDF対応）")

# ページ幅拡張
st.markdown(
    """
    <style>
    .main .block-container { max-width: 1800px !important; }
    </style>
    """,
    unsafe_allow_html=True
)

def azure_ocr(file_path, want_to_read=None):
    """Azure Computer Vision OCR（画像・PDF両対応、キーワード抽出対応）"""
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

# --- 1. ファイルアップロード ---
st.header("STEP 1: 画像またはPDFをアップロード（Azure OCR）")
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

    # --- 2. OCR実行 ---
    st.header("STEP 2: OCR実行・専用プロンプトでJson抽出")
    # Settings.jsonからPL専用プロンプトを読み込む
    pl_prompt = None
    try:
        with open("Settings.json", "r", encoding="utf-8") as f:
            settings = json.load(f)
            pl_prompt = settings.get("pl_prompt", None)
    except Exception:
        pl_prompt = None
    prompt_options = ["（自由入力）"]
    if pl_prompt:
        prompt_options.append("PL専用プロンプト")
    selected_prompt = st.selectbox("プロンプト選択", prompt_options, index=0)
    if selected_prompt == "PL専用プロンプト" and pl_prompt:
        default_prompt = pl_prompt
    else:
        default_prompt = ""
    custom_prompt = st.text_area(
        "Json抽出用プロンプト（任意。空欄の場合はデフォルトプロンプトを使用）",
        value=default_prompt,
        placeholder="例: 画像内の表をJson形式（{\"columns\": [...], \"data\": [[...], ...]}）で出力してください..."
    )
    want_to_read = st.text_input("抽出したいキーワード（カンマ区切りで複数指定可。空欄なら全文抽出）", value="")
    if st.button("Azure OCRでJson抽出実行", key="run_azure_ocr_json"):
        with st.spinner("Azure OCRで画像・PDFを解析中..."):
            try:
                # OCRテキスト抽出
                ocr_text = azure_ocr(save_path, want_to_read)
                # プロンプト生成
                if custom_prompt.strip():
                    prompt = custom_prompt.strip()
                else:
                    prompt = (
                        "画像内の表をJson形式（{\"columns\": [...], \"data\": [[...], ...]}）で出力してください。"
                        "絶対にJsonだけを返してください。解説や余計な文章は不要です。"
                        "テーブル内の空白セルも正確に抽出し、空欄は空文字列（\"\"）で出力してください。"
                    )
                # Azure OCRはテキスト抽出のみなので、AI APIでJson化する場合はここでAPI呼び出しが必要
                # ここでは仮にOCRテキストをプロンプトとともに表示（AI連携部分は要実装）
                st.info("OCRテキスト（AI連携部分は別途実装してください）:")
                st.text_area("OCRテキスト", value=ocr_text, height=200)
                st.info("プロンプト:")
                st.code(prompt, language="markdown")
                # --- ここでAI APIにocr_textとpromptを渡してJsonを得る処理を実装する想定 ---
                # 例: result_json = call_ai_api(ocr_text, prompt)
                # ここではダミーでパース失敗例を表示
                st.warning("※現状はOCRテキストとプロンプトの表示のみです。AI連携でJson化する場合はAPI呼び出しを実装してください。")
            except Exception as e:
                st.error(f"Azure OCR処理中にエラーが発生しました: {e}") 