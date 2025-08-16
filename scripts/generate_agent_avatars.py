#!/usr/bin/env python3
"""
example-agentディレクトリ内の各agentのアバター画像を生成するスクリプト

各JSONファイルから情報を読み取り、avatar_generator.pyを使用してアバター画像を生成します。
"""

import json
import asyncio
import sys
from pathlib import Path

# プロジェクトのsrcディレクトリをPythonパスに追加
project_root = Path(__file__).parent.parent
src_dir = project_root / "src"
sys.path.insert(0, str(src_dir))

from worklog_mcp.avatar_generator import generate_openai_avatar


class MockProjectContext:
    """プロジェクトコンテキストのモック実装"""
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        
    def get_avatar_path(self) -> str:
        """アバター保存ディレクトリパスを返す"""
        avatar_dir = self.project_path / "avatars"
        avatar_dir.mkdir(exist_ok=True)
        return str(avatar_dir)
    
    def get_database_path(self) -> str:
        """データベースパスを返す（今回は使用しないが必要）"""
        return str(self.project_path / "worklog.db")


async def generate_avatar_for_agent(agent_file: Path, project_context) -> bool:
    """単一のagentファイルからアバター画像を生成する"""
    try:
        # JSONファイルを読み込み
        with open(agent_file, 'r', encoding='utf-8') as f:
            agent_data = json.load(f)
        
        # 必要な情報を取得
        name = agent_data.get('name', '')
        role = agent_data.get('role', '')
        personality = agent_data.get('personality', '')
        appearance = agent_data.get('appearance', '')
        theme_color = agent_data.get('theme_color', 'Blue')
        user_id = agent_data.get('user_id', '')
        
        if not all([name, role, personality, appearance, user_id]):
            print(f"Warning: {agent_file.name} - 必要な情報が不足しています")
            return False
        
        # 既に画像が生成済みかチェック
        avatar_dir = Path(project_context.get_avatar_path())
        existing_avatar = avatar_dir / f"{user_id}_ai.png"
        
        if existing_avatar.exists():
            print(f"スキップ: {name} ({user_id}) - 既に画像が生成済みです")
            return True
        
        print(f"アバター生成開始: {name} ({user_id})")
        
        # OpenAI APIでアバター画像を生成（グラデーションは生成しない）
        avatar_path = await generate_openai_avatar(
            name=name,
            role=role,
            personality=personality,
            appearance=appearance,
            user_id=user_id,
            project_context=project_context
        )
        
        if avatar_path:
            print(f"アバター生成完了: {avatar_path}")
        else:
            print(f"アバター生成失敗（OpenAI APIエラー）: {user_id}")
            return False
        return True
        
    except Exception as e:
        print(f"Error: {agent_file.name} の処理中にエラーが発生: {e}")
        return False


async def main():
    """メイン処理"""
    # コマンドライン引数でプロジェクトパスを指定（デフォルトは現在のディレクトリ）
    if len(sys.argv) > 1:
        project_path = sys.argv[1]
    else:
        project_path = str(project_root)
    
    print(f"プロジェクトパス: {project_path}")
    
    # プロジェクトコンテキストを作成
    project_context = MockProjectContext(project_path)
    
    # example-agentディレクトリ
    example_agent_dir = project_root / "example-agent"
    
    if not example_agent_dir.exists():
        print(f"Error: {example_agent_dir} が存在しません")
        return
    
    success_count = 0
    total_count = 0
    
    # 各JSONファイルを処理
    json_files = sorted(example_agent_dir.glob("*.json"))
    
    print(f"{len(json_files)}個のagentファイルが見つかりました")
    print("-" * 50)
    
    for json_file in json_files:
        total_count += 1
        print(f"\n[{total_count}/{len(json_files)}] 処理中: {json_file.name}")
        
        if await generate_avatar_for_agent(json_file, project_context):
            success_count += 1
        
        # 待機（OpenAI API呼び出しのレート制限を考慮、2-3分かかるため）
        print(f"次のエージェントまで5秒待機...")
        await asyncio.sleep(5)
    
    print("-" * 50)
    print(f"\n処理完了: {success_count}/{total_count} エージェントのアバターが正常に生成されました")
    
    # 生成されたOpenAI生成アバターファイルを一覧表示
    avatar_dir = Path(project_context.get_avatar_path())
    ai_avatar_files = list(avatar_dir.glob("*_ai.png"))
    
    if ai_avatar_files:
        print(f"\n生成されたAIアバターファイル:")
        for avatar_file in sorted(ai_avatar_files):
            print(f"  - {avatar_file}")


if __name__ == "__main__":
    asyncio.run(main())