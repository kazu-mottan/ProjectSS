from PIL import Image
import io
import anthropic
import base64
import os
import streamlit as st
import sqlite3
from pdf2image import convert_from_path

class ClaudeVisionReader:
    def __init__(self, api_key=None, model="claude-3-7-sonnet-20250219"):
        # APIキーをANTHROPIC_API_KEY環境変数にセット
        if api_key:
            self.api_key = api_key
        else:
            try:
                self.api_key = st.secrets["claude_api_key"]
            except Exception:
                self.api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Claude APIキーが設定されていません。")
        os.environ["ANTHROPIC_API_KEY"] = self.api_key
        self.model = model
        self.client = anthropic.Anthropic(api_key=self.api_key)

    def resize_image_to_max_size(self, png_path, max_bytes=5*1024*1024):
        with open(png_path, "rb") as f:
            image_data = f.read()
        img = Image.open(io.BytesIO(image_data))
        # 画像モードをRGBまたはLに変換
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        # コントラストを強調
        from PIL import ImageEnhance
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.5)  # 1.0=元のまま, 1.5=やや強調
        # PNGはquality指定不可なのでサイズ縮小で対応
        width, height = img.size
        scale = 0.9
        while True:
            new_width = int(width * scale)
            new_height = int(height * scale)
            img_resized = img.resize((new_width, new_height), Image.LANCZOS)
            buf = io.BytesIO()
            img_resized.save(buf, format="PNG", optimize=True)
            data = buf.getvalue()
            if len(data) <= max_bytes or new_width < 100 or new_height < 100:
                return data
            scale -= 0.05
            if scale <= 0.1:
                break
        return data  # 最小まで縮小しても超える場合はそのまま返す

    def extract_info_from_png(self, file_path, prompt):
        """
        PNG画像から情報を抽出する
        """
        image_data = self.resize_image_to_max_size(file_path)
        image_base64 = base64.b64encode(image_data).decode("utf-8")
        message = self.client.messages.create(
            model=self.model,
            max_tokens=2048,  # より多くのトークンを許可
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": image_base64}},
                        {"type": "text", "text": prompt}
                    ]
                }
            ]
        )
        return message.content[0].text

    def extract_info_from_pdf(self, file_path, prompt):
        """
        PDFファイルから情報を抽出する（各ページごとに処理）
        """
        images = convert_from_path(file_path)
        results = []
        from PIL import ImageEnhance
        for i, img in enumerate(images):
            # 画像モードをRGBまたはLに変換
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            # コントラストを強調
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.5)
            buf = io.BytesIO()
            img.save(buf, format="PNG", optimize=True)
            image_data = buf.getvalue()
            if len(image_data) > 5*1024*1024:
                img = img.resize((int(img.width * 0.7), int(img.height * 0.7)), Image.LANCZOS)
                buf = io.BytesIO()
                img.save(buf, format="PNG", optimize=True)
                image_data = buf.getvalue()
            image_base64 = base64.b64encode(image_data).decode("utf-8")
            message = self.client.messages.create(
                model=self.model,
                max_tokens=2048,  # より多くのトークンを許可
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": image_base64}},
                            {"type": "text", "text": f"{prompt}（{i+1}ページ目）"}
                        ]
                    }
                ]
            )
            results.append(message.content[0].text)
        return "\n".join(results)

    def read_image_and_extract_info(self, file_path, prompt):
        """
        Claude Vision APIを使って画像（PNGまたはPDF）から情報を抽出する（anthropic SDK版）
        :param file_path: 画像またはPDFファイルのパス
        :param prompt: 画像から抽出したい内容を指示するプロンプト
        :return: Claudeの応答テキスト
        """
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".png":
            return self.extract_info_from_png(file_path, prompt)
        elif ext == ".pdf":
            return self.extract_info_from_pdf(file_path, prompt)
        else:
            raise ValueError("対応していないファイル形式です（png/pdfのみ）")

    @staticmethod
    def png_exists(filename, png_dir="png"):
        """pngディレクトリ内にファイルが存在するか確認（pdfも対応）"""
        return os.path.isfile(os.path.join(png_dir, filename))

    @staticmethod
    def make_ocr_prompt(want_to_read: str) -> str:
        """OCR用プロンプトを生成（日本語出力指示付き）"""
        return (
            f"この画像から「{want_to_read}」の内容を正確に抜き出してください。"
            "また、画像から何の情報から推測を行い、すべての単語・数字を正確に認識し、"
            "適切なスペースや改行を含めて出力してください。"
            "間違えやすい文字（例：Iと1、Oと0）に注意し、自然な文章として再構成せず、"
            "原文そのままを出力してください。"
            "【回答は必ず日本語で出力してください】"
        )

    @staticmethod
    def refine_japanese_text(text: str) -> str:
        """OpenAIで日本語として自然な文章に整形"""
        import openai
        import streamlit as st
        client = openai.OpenAI(api_key=st.secrets["openai_api_key"])
        prompt = (
            "以下のテキストを日本語として自然な文章に整形してください。"
            "句読点やスペース、改行も適切に修正し、読みやすくしてください。"
            "内容は変えず、誤字脱字や不自然な表現があれば直してください。\n\n"
            f"テキスト:\n{text}"
        )
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "あなたは日本語の文章校正の専門家です。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2048,
            temperature=0.2
        )
        return response.choices[0].message.content.strip()

    def ocr_and_refine(self, file_path: str, want_to_read: str) -> str:
        """OCR→日本語整形まで一括実行"""
        prompt = self.make_ocr_prompt(want_to_read)
        raw = self.read_image_and_extract_info(file_path, prompt)
        return self.refine_japanese_text(raw)

    def process_ocr_table(self, db_path, png_dir="png", target_ids=None):
        """
        qa.dbのocrテーブルを一括処理し、画像またはPDFからreference内容を抽出してresultに保存
        :param db_path: qa.dbのパス
        :param png_dir: png/pdfファイルのディレクトリ
        :param target_ids: 処理対象のocr.idリスト（Noneなら全件）
        """
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, filename, want_to_read FROM ocr")
        rows = cursor.fetchall()
        for row in rows:
            ocr_id, filename, want_to_read = row
            if target_ids and ocr_id not in target_ids:
                continue
            file_path = os.path.join(png_dir, filename)
            if not self.png_exists(filename, png_dir):
                print(f"ファイルが見つかりません: {file_path}")
                continue
            prompt = self.make_ocr_prompt(want_to_read)
            try:
                result = self.read_image_and_extract_info(file_path, prompt)
                print(f"[Claude OCR LOG] id={ocr_id}, filename={filename}, want_to_read={want_to_read}, result={result}")
                cursor.execute("UPDATE ocr SET result = ? WHERE id = ?", (result, ocr_id))
                conn.commit()
            except Exception as e:
                print(f"Claude Visionエラー: {e}")
        conn.close()

    def get_ocr_entries_with_images(self, db_path, png_dir="png"):
        """
        ocrテーブルの内容と画像/ファイルパスをリストで返す。
        type: 'image' or 'pdf' を付与。
        """
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, filename, want_to_read, result FROM ocr")
        rows = cursor.fetchall()
        entries = []
        for row in rows:
            ocr_id, filename, want_to_read, result = row
            file_path = os.path.join(png_dir, filename)
            ext = os.path.splitext(filename)[1].lower()
            if ext in [".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tiff"]:
                entry_type = "image"
            elif ext == ".pdf":
                entry_type = "pdf"
            else:
                entry_type = "other"
            entries.append({
                "id": ocr_id,
                "filename": filename,
                "want_to_read": want_to_read,
                "result": result,
                "file_path": file_path,
                "type": entry_type
            })
        conn.close()
        return entries

    def upload_and_label_file(self, db_path, png_dir="png"):
        st.subheader("PNGまたはPDFファイルのアップロードと業種・項目指定")
        uploaded_file = st.file_uploader("ファイルを選択してください（PNGまたはPDF）", type=["png", "pdf"])
        if uploaded_file is not None:
            # 保存先ディレクトリがなければ作成
            if not os.path.exists(png_dir):
                os.makedirs(png_dir)
            # ファイル保存
            save_path = os.path.join(png_dir, uploaded_file.name)
            with open(save_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.success(f"ファイルを保存しました: {save_path}")

            # 業種選択
            label = st.selectbox("業種", ["不動産", "保険"], key=f"label_{uploaded_file.name}")
            # 読み取りたい項目
            want_to_read = st.text_input("読み取りたい項目", key=f"want_to_read_{uploaded_file.name}")
            if st.button("登録", key=f"register_label_{uploaded_file.name}"):
                # DBに登録
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO ocr (filename, want_to_read, label) VALUES (?, ?, ?)",
                    (uploaded_file.name, want_to_read, label)
                )
                conn.commit()
                conn.close()
                st.success("ファイル・業種・項目をデータベースに登録しました。")

    def openai_ocr_image(self, file_path, prompt):
        """
        OpenAI Vision APIで画像（PNG）から情報を抽出する（openai>=1.0.0新SDK対応）
        """
        from openai import OpenAI
        import base64
        client = OpenAI(api_key=st.secrets["openai_api_key"])
        with open(file_path, "rb") as f:
            image_data = f.read()
        image_base64 = base64.b64encode(image_data).decode()
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}}
                    ]
                }
            ],
            max_tokens=2048
        )
        return response.choices[0].message.content

    def openai_ocr_pdf(self, file_path, prompt):
        """
        OpenAI Vision APIでPDF（各ページ画像化）から情報を抽出する（openai>=1.0.0新SDK対応）
        """
        from openai import OpenAI
        import base64
        from pdf2image import convert_from_path
        client = OpenAI(api_key=st.secrets["openai_api_key"])
        images = convert_from_path(file_path)
        results = []
        for i, img in enumerate(images):
            buf = io.BytesIO()
            img.save(buf, format="PNG", optimize=True)
            image_data = buf.getvalue()
            image_base64 = base64.b64encode(image_data).decode()
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": f"{prompt}（{i+1}ページ目）"},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}}
                        ]
                    }
                ],
                max_tokens=2048
            )
            results.append(response.choices[0].message.content)
        return "\n".join(results)

    def openai_read_image_and_extract_info(self, file_path, prompt):
        """
        OpenAI Vision APIで画像（PNGまたはPDF）から情報を抽出する
        """
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".png":
            return self.openai_ocr_image(file_path, prompt)
        elif ext == ".pdf":
            return self.openai_ocr_pdf(file_path, prompt)
        else:
            raise ValueError("対応していないファイル形式です（png/pdfのみ）")

# 使い方例:
# from modules.claude_vision_reader import ClaudeVisionReader
# reader = ClaudeVisionReader()  # APIキーはsecrets.tomlから自動取得
# result = reader.read_image_and_extract_info("sample.png", "この画像から表の合計金額を抜き出して")
# print(result)
#
# PDF例:
# result = reader.read_image_and_extract_info("sample.pdf", "このPDFから表の合計金額を抜き出して")
# print(result)
#
# OCRテーブル一括処理例:
# reader.process_ocr_table("../db/qa.db", png_dir="png")

# この部分は削除してください 