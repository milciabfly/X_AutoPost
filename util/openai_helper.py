"""
OpenAI API関連のヘルパー関数
"""
import os
from openai import OpenAI


def compose_with_openai(original_text: str, prompt: str, max_chars: int = 50, position: str = "after") -> str:
    """
    OpenAI APIを使用してツイート文を生成・編集
    
    Args:
        original_text: 元のツイート本文
        prompt: OpenAIへのプロンプト（ユーザー指示）
        max_chars: 追加する文字数の最大値
        position: 追加位置 ("before" または "after")
    
    Returns:
        編集後のツイート本文
    """
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY が設定されていません")
    
    if not prompt or not prompt.strip():
        raise ValueError("プロンプトが入力されていません")
    
    client = OpenAI(api_key=api_key)
    
    # プロンプト構築: ユーザー入力のプロンプトのみを使用（ツイート内容は参照しない）
    user_message = f"{prompt}\n\n制約: {max_chars}文字以内で生成してください。"
    
    # OpenAI APIコール
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "あなたはTwitter投稿の補助AIです。指示に従って簡潔な文章を生成してください。"},
            {"role": "user", "content": user_message}
        ],
        max_tokens=200,
        temperature=0.7
    )
    
    generated = response.choices[0].message.content.strip()
    
    # 位置に応じて結合
    if position == "before":
        return f"{generated}\n\n{original_text}"
    else:  # after
        return f"{original_text}\n\n{generated}"
