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
    import logging
    import time

    logger = logging.getLogger(__name__)

    try:
        from openai import OpenAI

        # 環境変数からAPIキーを取得
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.info(
                "OpenAI APIキーが設定されていません。フォールバックでグラデーション画像を使用します。"
            )
            return None

        prompt = f"""
下記人物のバストアップの証明写真風の写真を生成してください。
文字情報は一切画像に含めないこと。
背景は透明。

## 名前
{name}

## 役割
{role}

## 性格
{personality}

## 外見
{appearance}
"""

        logger.info(f"OpenAI API呼び出し開始 - ユーザー: {name} (ID: {user_id})")
        logger.debug(f"OpenAI APIプロンプト: {prompt}")

        client = OpenAI(api_key=api_key)

        start_time = time.time()
        response = client.responses.create(
            model="gpt-5",
            input=prompt,
            tools=[
                {
                    "type": "image_generation",
                    "background": "transparent",
                    "quality": "high",
                    "size": "1024x1024",
                }
            ],
        )
        end_time = time.time()

        logger.info(f"OpenAI API呼び出し完了 - 時間: {end_time - start_time:.2f}秒")

        image_data = [
            output.result
            for output in response.output
            if output.type == "image_generation_call"
        ]

        if not image_data:
            logger.warning("OpenAI APIから画像データが返されませんでした")
            return None

        image_base64 = image_data[0]
        logger.debug(f"受信した画像データサイズ: {len(image_base64)} bytes (base64)")

        # プロジェクト専用のアバターディレクトリパスを取得
        avatar_dir = Path(project_context.get_avatar_path())

        # ディレクトリが存在しない場合は作成
        avatar_dir.mkdir(parents=True, exist_ok=True)

        avatar_path = avatar_dir / f"{user_id}_ai.png"
        logger.debug(f"アバター保存先: {avatar_path}")

        async with aiofiles.open(avatar_path, "wb") as f:
            await f.write(base64.b64decode(image_base64))

        logger.info(f"OpenAI生成アバター保存完了: {avatar_path}")
        return str(avatar_path)

    except Exception as e:
        # OpenAI APIでエラーが発生した場合はNoneを返してフォールバックに
        error_type = type(e).__name__

        # OpenAI固有のエラーの場合、より詳細な情報をログに記録
        if hasattr(e, "code") and hasattr(e, "message"):
            logger.error(
                f"OpenAI API呼び出しエラー: {error_type} (code: {e.code}): {e.message}"
            )
        elif hasattr(e, "status_code"):
            logger.error(
                f"OpenAI API呼び出しエラー: {error_type} (status: {e.status_code}): {e}"
            )
        else:
            logger.error(f"OpenAI API呼び出しエラー: {error_type}: {e}")

        logger.debug("OpenAI APIエラー詳細", exc_info=True)
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

    # 外側から内側に向かってグラデーション（最適化：ステップを大きくして描画回数を半減）
    for i in range(radius, 0, -10):
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

    avatar_path = avatar_dir / f"{user_id}_gradient.png"
    # PNG保存最適化：圧縮レベルを下げて保存時間を短縮
    img.save(avatar_path, "PNG", optimize=False, compress_level=1)

    return str(avatar_path)


async def generate_user_avatar_async(
    name: str,
    role: str,
    personality: str,
    appearance: str,
    theme_color: str,
    user_id: str,
    project_context,
) -> None:
    """ユーザーのアバター画像を非同期で生成する（バックグラウンド実行用）

    OpenAI APIが利用可能な場合はAI生成、そうでなければグラデーション画像を生成
    生成完了後、データベースのアバターパスを更新

    Args:
        name: ユーザー名
        role: 役割
        personality: 性格
        appearance: 外見
        theme_color: テーマカラー
        user_id: ユーザーID
        project_context: プロジェクトコンテキスト
    """
    try:
        # まずOpenAI APIでの生成を試行
        openai_path = await generate_openai_avatar(
            name, role, personality, appearance, user_id, project_context
        )

        if openai_path:
            # AI生成が成功した場合のみデータベース更新と通知を実行
            avatar_path = openai_path

            # データベースのアバターパスを更新
            from .database import Database

            db = Database(project_context.get_database_path())
            await db.update_user_avatar_path(user_id, avatar_path)

            # Webサーバーに通知（AI生成完了時のみ）
            # web_serverがインポート可能か確認して通知
            try:
                from . import tools

                if hasattr(tools, "web_server") and tools.web_server:
                    await tools.web_server.notify_clients(
                        "avatar_updated",
                        {"user_id": user_id, "avatar_path": avatar_path},
                    )
            except Exception as e:
                # Web通知に失敗してもアバター生成処理は継続
                import logging

                logger = logging.getLogger(__name__)
                logger.debug(f"アバター更新通知に失敗（処理は継続）: {e}")

    except Exception as e:
        # エラーが発生した場合もフォールバックを試行
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"アバター生成処理でエラーが発生: {type(e).__name__}: {e}")
        logger.debug("アバター生成エラー詳細", exc_info=True)

        # エラー発生時はグラデーション画像がそのまま使用される
        logger.info("AI生成に失敗しましたが、既存のグラデーション画像が使用されます")


async def generate_user_avatar(
    name: str,
    role: str,
    personality: str,
    appearance: str,
    theme_color: str,
    user_id: str,
    project_context,
) -> str:
    """ユーザーのアバター画像を生成する（即座にフォールバック画像を返す）

    即座にグラデーション画像を生成して返し、バックグラウンドでOpenAI生成を試行

    Args:
        name: ユーザー名
        role: 役割
        personality: 性格
        appearance: 外見
        theme_color: テーマカラー
        user_id: ユーザーID
        project_context: プロジェクトコンテキスト

    Returns:
        生成された画像ファイルのパス（即座にグラデーション画像）
    """
    # 即座にグラデーション画像を生成して返す
    avatar_path = await generate_gradient_avatar(theme_color, user_id, project_context)

    # バックグラウンドでOpenAI生成を開始（結果は待たない）
    import asyncio

    asyncio.create_task(
        generate_user_avatar_async(
            name, role, personality, appearance, theme_color, user_id, project_context
        )
    )

    return avatar_path
