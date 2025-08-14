"""アバター画像生成機能"""

import os
import base64
from pathlib import Path
from typing import Optional
from PIL import Image, ImageDraw
import aiofiles


async def generate_openai_avatar(
    name: str,
    role: str,
    personality: str,
    appearance: str,
    user_id: str,
    project_context,
) -> Optional[str]:
    """OpenAI APIを使用してアバター画像を生成する

    Args:
        name: ユーザー名
        role: 役割
        personality: 性格
        appearance: 外見
        user_id: ユーザーID

    Returns:
        生成された画像ファイルのパス（失敗時はNone）
    """
    try:
        from openai import OpenAI

        # 環境変数からAPIキーを取得
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None

        prompt = f"""
下記人物のバストアップの証明写真風の写真を生成してください。
背景は透過。

## 名前
{name}

## 役割
{role}

## 性格
{personality}

## 外見
{appearance}
"""

        client = OpenAI(api_key=api_key)
        response = client.responses.create(
            model="gpt-5",
            input=prompt,
            tools=[
                {
                    "type": "image_generation",
                    "background": "transparent",
                    "quality": "high",
                    "size": "1024x1024"
                }
            ],
        )

        image_data = [
            output.result
            for output in response.output
            if output.type == "image_generation_call"
        ]

        if not image_data:
            return None

        image_base64 = image_data[0]

        # プロジェクト専用のアバターディレクトリパスを取得
        avatar_dir = Path(project_context.get_avatar_path())

        avatar_path = avatar_dir / f"{user_id}.png"

        async with aiofiles.open(avatar_path, "wb") as f:
            await f.write(base64.b64decode(image_base64))

        return str(avatar_path)

    except Exception:
        # OpenAI APIでエラーが発生した場合はNoneを返してフォールバックに
        return None


async def generate_gradient_avatar(
    theme_color: str, user_id: str, project_context
) -> str:
    """テーマカラーの単色グラデーション丸画像を生成する（フォールバック用）

    Args:
        theme_color: テーマカラー
        user_id: ユーザーID

    Returns:
        生成された画像ファイルのパス
    """
    # カラーマッピング
    color_map = {
        "Red": (255, 100, 100),
        "Blue": (100, 150, 255),
        "Green": (100, 200, 100),
        "Yellow": (255, 220, 100),
        "Purple": (200, 100, 255),
        "Orange": (255, 150, 100),
        "Pink": (255, 150, 200),
        "Cyan": (100, 200, 255),
    }

    base_color = color_map.get(theme_color, (100, 150, 255))  # デフォルトはBlue

    # 512x512の透明背景画像を作成
    size = 512
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # グラデーション効果のため、中心から外側に向かって複数の円を描画
    center = size // 2
    radius = center - 10

    # 外側から内側に向かってグラデーション
    for i in range(radius, 0, -5):
        # アルファ値と色の明度を調整してグラデーション効果を作成
        alpha = int(255 * (i / radius) * 0.8)  # 外側ほど薄く
        brightness = 0.6 + 0.4 * (i / radius)  # 外側ほど明るく

        color = tuple(int(c * brightness) for c in base_color) + (alpha,)

        left = center - i
        top = center - i
        right = center + i
        bottom = center + i

        draw.ellipse([left, top, right, bottom], fill=color)

    # プロジェクト専用のアバターディレクトリパスを取得
    avatar_dir = Path(project_context.get_avatar_path())

    avatar_path = avatar_dir / f"{user_id}.png"
    img.save(avatar_path, "PNG")

    return str(avatar_path)


async def generate_user_avatar(
    name: str,
    role: str,
    personality: str,
    appearance: str,
    theme_color: str,
    user_id: str,
    project_context,
) -> str:
    """ユーザーのアバター画像を生成する

    OpenAI APIが利用可能な場合はAI生成、そうでなければグラデーション画像を生成

    Args:
        name: ユーザー名
        role: 役割
        personality: 性格
        appearance: 外見
        theme_color: テーマカラー
        user_id: ユーザーID

    Returns:
        生成された画像ファイルのパス
    """
    # まずOpenAI APIでの生成を試行
    openai_path = await generate_openai_avatar(
        name, role, personality, appearance, user_id, project_context
    )

    if openai_path:
        return openai_path

    # フォールバック: グラデーション画像を生成
    return await generate_gradient_avatar(theme_color, user_id, project_context)
