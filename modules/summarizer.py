import streamlit as st
from openai import OpenAI
import tiktoken
import re

def count_tokens(text):
    """テキストのトークン数をカウント"""
    encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
    return len(encoding.encode(text))

def split_text(text, max_tokens=3000):
    """
    テキストを適切なサイズに分割
    
    Args:
        text (str): 分割するテキスト
        max_tokens (int): 1チャンクあたりの最大トークン数
        
    Returns:
        list: 分割されたテキストのリスト
    """
    # 文単位で分割
    sentences = text.split('。')
    chunks = []
    current_chunk = []
    current_tokens = 0
    
    for sentence in sentences:
        sentence_tokens = count_tokens(sentence)
        if current_tokens + sentence_tokens > max_tokens and current_chunk:
            chunks.append('。'.join(current_chunk) + '。')
            current_chunk = []
            current_tokens = 0
        
        current_chunk.append(sentence)
        current_tokens += sentence_tokens
    
    if current_chunk:
        chunks.append('。'.join(current_chunk) + '。')
    
    return chunks

def format_conversation(text):
    """
    テキストを会話形式に整形
    
    Args:
        text (str): 整形するテキスト
        
    Returns:
        str: 整形された会話テキスト
    """
    try:
        prompt = f"""
        以下のテキストを自然な日本語の会話形式に整形してください。
        以下のルールに従って整形してください：
        
        1. 話者の区別
        - 話者を明確に区別し、「話者A:」「話者B:」などの形式で表示
        - 話者の発言は必ず「話者名: 発言内容」の形式にする
        - 話者の発言は改行で区切る
        
        2. 会話の自然さ
        - 日本語として自然な表現を使用
        - 敬語や丁寧語の使い方を統一
        - 話し言葉として自然な表現に修正
        - 不自然な言い回しを避ける
        
        3. 文脈の保持
        - 会話の流れを自然に保つ
        - 重要な情報は漏れなく含める
        - 会話の区切りや重要なポイントは空行を入れて強調
        
        4. 形式の統一
        - 不自然な改行や空白を整理
        - 句読点の使い方を統一
        - 余分な空白を削除
        
        テキスト:
        {text}
        """
        
        client = OpenAI(api_key=st.secrets["openai_api_key"])
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "あなたは日本語の会話記録を整形する専門家です。自然な日本語表現を使用し、話者を明確に区別し、会話の流れを保ちながら、重要なポイントを強調してください。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=2000
        )
        
        # 整形されたテキストをさらに整理
        formatted_text = response.choices[0].message.content
        
        # 空行の整理（2行以上の空行を1行に）
        formatted_text = re.sub(r'\n\s*\n', '\n\n', formatted_text)
        
        # 話者の発言形式の統一（コロンの後の空白を統一）
        formatted_text = re.sub(r'([^:]+):\s*', r'\1: ', formatted_text)
        
        # 余分な空白の削除（2つ以上の空白を1つに）
        formatted_text = re.sub(r' +', ' ', formatted_text)
        
        # 句読点の統一（全角に統一）
        formatted_text = formatted_text.replace('。', '。').replace('、', '、')
        
        return formatted_text.strip()
    except Exception as e:
        st.error(f"会話整形中にエラーが発生しました: {str(e)}")
        return text

def summarize_chunk(chunk):
    """
    テキストのチャンクを要約
    
    Args:
        chunk (str): 要約するテキストのチャンク
        
    Returns:
        str: 要約結果
    """
    try:
        prompt = f"""
        以下のテキストを要約してください。
        重要なポイントを漏れなく抽出し、簡潔にまとめてください。
        
        テキスト:
        {chunk}
        """
        
        client = OpenAI(api_key=st.secrets["openai_api_key"])
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "あなたはテキストを要約する専門家です。重要なポイントを漏れなく抽出し、簡潔にまとめてください。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=2000
        )
        
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"チャンク要約中にエラーが発生しました: {str(e)}")
        return ""

def merge_summaries(summaries):
    """
    複数の要約を統合
    
    Args:
        summaries (list): 要約のリスト
        
    Returns:
        str: 統合された要約
    """
    if not summaries:
        return ""
    
    if len(summaries) == 1:
        return summaries[0]
    
    try:
        prompt = f"""
        以下の複数の要約を統合し、1つの要約にまとめてください。
        重複を避け、重要なポイントを漏れなく含めてください。
        
        要約:
        {chr(10).join(summaries)}
        """
        
        client = OpenAI(api_key=st.secrets["openai_api_key"])
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "あなたは複数の要約を統合する専門家です。重複を避け、重要なポイントを漏れなく含めてください。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=2000
        )
        
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"要約統合中にエラーが発生しました: {str(e)}")
        return chr(10).join(summaries)  # エラー時は単純に結合

def summarize(text):
    """
    テキストを要約する関数
    
    Args:
        text (str): 要約するテキスト
        
    Returns:
        str: 要約結果
    """
    try:
        # テキストを会話形式に整形
        formatted_text = format_conversation(text)
        
        # テキストを分割
        chunks = split_text(formatted_text)
        summaries = []
        
        # プログレスバーの設定
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # 各チャンクを要約
        for i, chunk in enumerate(chunks):
            status_text.text(f"要約中... ({i+1}/{len(chunks)})")
            summary = summarize_chunk(chunk)
            summaries.append(summary)
            progress_bar.progress((i + 1) / len(chunks))
        
        # 要約を統合
        final_summary = merge_summaries(summaries)
        return formatted_text, final_summary
        
    except Exception as e:
        st.error(f"要約中にエラーが発生しました: {str(e)}")
        return text, ""
    