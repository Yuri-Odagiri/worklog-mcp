#!/usr/bin/env python3
"""
ダミーデータ投入スクリプト
worklog-mcpプロジェクトのデータベースにダミーデータを投入します
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from pathlib import Path
import sys
import argparse
import random

# プロジェクトルートのsrcディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from worklog_mcp.database import Database
from worklog_mcp.models import User, WorklogEntry


# ダミーユーザーデータ
DUMMY_USERS = [
    {
        "user_id": "tanaka", 
        "name": "田中太郎",
        "theme_color": "Blue",
        "role": "チームリーダー",
        "personality": "責任感が強く、チームを引っ張る性格です。",
        "appearance": "凛とした佇まいで、頼りになる雰囲気を持っています。"
    },
    {
        "user_id": "yamada", 
        "name": "山田花子",
        "theme_color": "Pink",
        "role": "デザイナー",
        "personality": "創造性豊かで、美的センスに優れています。",
        "appearance": "おしゃれで洗練されたスタイルを好みます。"
    },
    {
        "user_id": "sato", 
        "name": "佐藤次郎",
        "theme_color": "Green",
        "role": "エンジニア",
        "personality": "論理的思考が得意で、問題解決能力に長けています。",
        "appearance": "カジュアルだが整った服装で、集中力の高さが表情に現れています。"
    },
    {
        "user_id": "suzuki", 
        "name": "鈴木美咲",
        "theme_color": "Purple",
        "role": "プロダクトマネージャー",
        "personality": "コミュニケーション能力が高く、調整力に優れています。",
        "appearance": "明るい笑顔が印象的で、親しみやすい雰囲気を持っています。"
    },
    {
        "user_id": "takahashi", 
        "name": "高橋健一",
        "theme_color": "Orange",
        "role": "品質保証エンジニア",
        "personality": "細かいところまで気を配る完璧主義者です。",
        "appearance": "落ち着いた雰囲気で、常に冷静沈着な印象を与えます。"
    },
]

# ダミー分報コンテンツのテンプレート
WORKLOG_TEMPLATES = [
    # 作業開始系
    "## 作業開始\n今日も一日頑張ります！☕",
    "## 朝会完了\n今日のタスク:\n- [ ] {task1}\n- [ ] {task2}\n- [ ] {task3}",
    "## 出社\n今日は{weather}ですね。{time}から作業開始します。",
    
    # 作業中系
    "## {feature}の実装中\n現在{progress}%完了。順調に進んでいます。",
    "## バグ修正\n`{bug}`を修正中。原因は{cause}っぽい。",
    "## コードレビュー\n{pr}のレビュー中。{comment}",
    "## ミーティング\n{meeting}に参加中。{topic}について議論中。",
    
    # 技術系
    "## 調査メモ\n{tech}について調査中。\n```python\n{code}\n```\n意外と便利かも。",
    "## エラー対応\n```\n{error}\n```\nこのエラーで詰まってる...",
    "## 解決！\nさっきのエラー、{solution}で解決しました！",
    
    # 休憩系
    "## 休憩\nコーヒーブレイク☕ {snack}食べてます。",
    "## ランチ\n今日のランチは{lunch}。美味しかった！",
    
    # 完了系
    "## タスク完了\n- [x] {completed_task}\n無事完了しました！",
    "## PR作成\n{pr_title}のPRを作成しました。\nレビューお願いします🙏",
    "## デプロイ完了\n{env}環境にデプロイ完了。動作確認OK✅",
    
    # 振り返り系
    "## 今日の振り返り\n- 完了: {done}\n- 未完了: {todo}\n- 明日やること: {tomorrow}",
    "## 退勤\n今日も一日お疲れ様でした！🌙",
]

# ランダムデータ生成用の辞書
RANDOM_DATA = {
    "task1": ["API実装", "UI改修", "テスト追加", "ドキュメント更新", "バグ修正"],
    "task2": ["コードレビュー", "リファクタリング", "パフォーマンス改善", "セキュリティ対応", "CI/CD改善"],
    "task3": ["ミーティング参加", "調査タスク", "設計書作成", "リリース準備", "環境構築"],
    "weather": ["晴れ", "曇り", "雨", "快晴", "肌寒い日"],
    "time": ["9:00", "9:30", "10:00", "10:30", "11:00"],
    "feature": ["ユーザー認証", "検索機能", "通知機能", "ダッシュボード", "レポート機能"],
    "progress": [20, 40, 50, 60, 80, 90],
    "bug": ["NullPointerException", "型エラー", "無限ループ", "メモリリーク", "デッドロック"],
    "cause": ["初期化漏れ", "型の不一致", "同期処理のミス", "キャッシュの問題", "設定ミス"],
    "pr": ["#123", "#456", "#789", "#234", "#567"],
    "comment": ["良いアプローチだと思います", "ここは要修正かも", "LGTMです！", "テスト追加お願いします", "素晴らしい実装です"],
    "meeting": ["朝会", "夕会", "定例会", "設計レビュー", "振り返り会"],
    "topic": ["今週の進捗", "来週の計画", "技術選定", "アーキテクチャ", "リリース計画"],
    "tech": ["React Hooks", "TypeScript", "Docker", "GraphQL", "WebSocket"],
    "code": ["const result = await fetch('/api/data')", "useEffect(() => {...}, [])", "docker-compose up -d", "SELECT * FROM users", "git rebase -i HEAD~3"],
    "error": ["TypeError: Cannot read property 'x' of undefined", "Connection refused", "404 Not Found", "CORS policy error", "Timeout exceeded"],
    "solution": ["nullチェックを追加", "ポート番号を修正", "URLを修正", "CORS設定を追加", "タイムアウト値を増やす"],
    "snack": ["クッキー", "チョコレート", "せんべい", "ナッツ", "フルーツ"],
    "lunch": ["ラーメン", "カレー", "パスタ", "寿司", "サンドイッチ"],
    "completed_task": ["API実装", "バグ修正", "テスト作成", "ドキュメント更新", "コードレビュー"],
    "pr_title": ["feat: ユーザー認証機能追加", "fix: メモリリーク修正", "docs: README更新", "refactor: コード整理", "test: ユニットテスト追加"],
    "env": ["開発", "ステージング", "本番", "テスト", "デモ"],
    "done": ["3つのタスク", "バグ修正2件", "ミーティング2回", "コードレビュー1件", "ドキュメント作成"],
    "todo": ["テスト追加", "リファクタリング", "パフォーマンス測定", "エラー処理", "ログ追加"],
    "tomorrow": ["残タスクの完了", "新機能の実装開始", "定例会参加", "コードレビュー", "調査タスク"],
}


def generate_worklog_content(template: str) -> str:
    """テンプレートからランダムな分報コンテンツを生成"""
    content = template
    for key, values in RANDOM_DATA.items():
        placeholder = f"{{{key}}}"
        if placeholder in content:
            value = random.choice(values)
            content = content.replace(placeholder, str(value))
    return content


async def seed_dummy_data(project_name: str, days: int = 7, entries_per_day: int = 10):
    """ダミーデータを投入する
    
    Args:
        project_name: プロジェクト名
        days: 何日分のデータを生成するか
        entries_per_day: 1日あたりのエントリー数（ユーザーあたり）
    """
    db_path = Path.home() / ".worklog" / project_name / "database" / "worklog.db"
    
    if not db_path.exists():
        print(f"エラー: データベース {db_path} が存在しません。")
        print("先に init_db.py を実行してください。")
        return
    
    db_file_path = str(Path.home() / ".worklog" / project_name / "database" / "worklog.db")
    db = Database(db_file_path)
    
    print(f"ダミーデータを投入中: {db_path}")
    print(f"設定: {days}日分、1日あたり{entries_per_day}エントリー/ユーザー")
    
    # ユーザーを作成
    print("\nユーザーを作成中...")
    for user_data in DUMMY_USERS:
        user = User(**user_data)
        await db.create_user(user)
        print(f"  ✓ {user.name} ({user.user_id})")
    
    # 分報エントリーを作成
    print("\n分報エントリーを作成中...")
    now = datetime.now()
    entry_count = 0
    thread_parents = []  # スレッド返信用の親エントリー
    
    for day in range(days):
        base_date = now - timedelta(days=days - day - 1)
        
        for user_data in DUMMY_USERS:
            user_id = user_data["user_id"]
            
            # その日の分報を時系列で生成
            for hour in range(entries_per_day):
                # 時刻をランダムに設定（9:00-18:00の間）
                entry_time = base_date.replace(
                    hour=9 + hour % 10,
                    minute=random.randint(0, 59),
                    second=random.randint(0, 59)
                )
                
                # テンプレートをランダムに選択
                template = random.choice(WORKLOG_TEMPLATES)
                content = generate_worklog_content(template)
                
                # たまにスレッド返信を作成（10%の確率）
                related_entry_id = None
                if thread_parents and random.random() < 0.1:
                    parent = random.choice(thread_parents)
                    related_entry_id = parent.id
                    content = f"@{parent.user_id} {content}"
                
                entry = WorklogEntry(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    markdown_content=content,
                    related_entry_id=related_entry_id,
                    created_at=entry_time,
                    updated_at=entry_time
                )
                
                await db.create_entry(entry)
                entry_count += 1
                
                # 親エントリーとして記録（スレッド用）
                if not related_entry_id and random.random() < 0.3:
                    thread_parents.append(entry)
                    # 古いエントリーは削除（メモリ節約）
                    if len(thread_parents) > 20:
                        thread_parents.pop(0)
                
                # 進捗表示
                if entry_count % 50 == 0:
                    print(f"  {entry_count} エントリー作成済み...")
    
    print(f"\n✓ 合計 {entry_count} エントリーを作成しました！")
    
    # 統計情報を表示
    print("\n=== データベース統計 ===")
    
    import aiosqlite
    async with aiosqlite.connect(db_file_path) as conn:
        # ユーザー数
        cursor = await conn.execute("SELECT COUNT(*) FROM users")
        user_count = (await cursor.fetchone())[0]
        print(f"ユーザー数: {user_count}")
        
        # エントリー数
        cursor = await conn.execute("SELECT COUNT(*) FROM entries")
        total_entries = (await cursor.fetchone())[0]
        print(f"総エントリー数: {total_entries}")
        
        # スレッド数
        cursor = await conn.execute("SELECT COUNT(*) FROM entries WHERE related_entry_id IS NOT NULL")
        thread_count = (await cursor.fetchone())[0]
        print(f"スレッド返信数: {thread_count}")
    
    # ユーザー別統計
    print("\n=== ユーザー別統計 ===")
    for user_data in DUMMY_USERS:
        user_id = user_data["user_id"]
        stats = await db.get_user_stats(user_id)
        print(f"{user_data['name']} ({user_id}):")
        print(f"  - 総投稿数: {stats['total_posts']}")
        print(f"  - 今日の投稿数: {stats['today_posts']}")
        if stats['first_post']:
            print(f"  - 初投稿: {stats['first_post']}")
            print(f"  - 最終投稿: {stats['latest_post']}")
    print("\nダミーデータの投入が完了しました！")


def main():
    """メインエントリーポイント"""
    parser = argparse.ArgumentParser(
        description="worklog-mcpプロジェクトのデータベースにダミーデータを投入します"
    )
    parser.add_argument(
        "--project",
        "-p",
        default="worklog-mcp",
        help="プロジェクト名 (デフォルト: worklog-mcp)"
    )
    parser.add_argument(
        "--days",
        "-d",
        type=int,
        default=7,
        help="生成する日数 (デフォルト: 7)"
    )
    parser.add_argument(
        "--entries-per-day",
        "-e",
        type=int,
        default=10,
        help="1日あたりのエントリー数/ユーザー (デフォルト: 10)"
    )
    
    args = parser.parse_args()
    
    try:
        asyncio.run(seed_dummy_data(
            args.project,
            args.days,
            args.entries_per_day
        ))
    except KeyboardInterrupt:
        print("\n処理を中断しました")
        sys.exit(1)
    except Exception as e:
        print(f"エラーが発生しました: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()