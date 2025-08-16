"""
Agent MCP Server - ユーザーエージェント対話ツール

指定したuser(agent)に話しかける機能を提供
呼び出し元と相手のuser_idの組に対してsession_idは1つというモデル
"""

import logging
import json
import aiosqlite
from mcp.server.fastmcp import FastMCP, Context

logger = logging.getLogger(__name__)


def register_agent_tools(
    mcp: FastMCP,
    database: "Database",
    project_context: "ProjectContext",
) -> None:
    """ユーザーエージェント対話ツールを登録"""
    
    from ..server import PersonalizedWorklogAgent
    from ..agent_session import AgentSessionManager
    
    # エージェント専用データベースパス（プロジェクト別）
    agent_db_path = project_context.get_database_path().replace(".db", "_agent.db")
    session_manager = AgentSessionManager(agent_db_path)
    
    # パーソナライズドエージェントマネージャー初期化
    agent_manager = PersonalizedWorklogAgent(database, project_context, session_manager)
    
    # セッション管理初期化（非同期なので実行時に初期化）
    async def ensure_session_init():
        await session_manager.initialize()
    
    @mcp.tool(
        name="talk_to_user_agent",
        description="指定したユーザー（エージェント）に話しかけます。そのユーザーの人格設定に基づいてパーソナライズされた応答を得られます。"
    )
    async def talk_to_user_agent(
        caller_user_id: str,
        target_user_id: str,
        message: str,
        ctx: Context
    ) -> str:
        """指定したユーザーエージェントと対話
        
        Args:
            caller_user_id: 呼び出し元のユーザーID
            target_user_id: 対話相手のユーザーID（エージェント）
            message: 送信するメッセージ
        """
        try:
            # セッション管理初期化
            await ensure_session_init()
            
            # 呼び出し元ユーザー確認
            caller_user = await database.get_user(caller_user_id)
            if not caller_user:
                raise ValueError(f"呼び出し元ユーザーID '{caller_user_id}' が見つかりません")
            
            # 対話相手ユーザー確認
            target_user = await database.get_user(target_user_id)
            if not target_user:
                raise ValueError(f"対話相手ユーザーID '{target_user_id}' が見つかりません")
            
            # 自分自身との対話を禁止
            if caller_user_id == target_user_id:
                raise ValueError("自分自身とは対話できません")
            
            logger.info(f"Agent conversation: {caller_user.name} -> {target_user.name}")
            
            # セッション取得または作成
            session_id = await session_manager.get_or_create_session(
                caller_user_id,
                target_user_id,
                project_context.project_path,
                {
                    "conversation_type": "user_agent_talk",
                    "caller_name": caller_user.name,
                    "target_name": target_user.name
                }
            )
            
            # 対話相手の人格に基づくパーソナライズドエージェント作成
            agent = await agent_manager.create_personalized_agent(target_user_id)
            
            # 対話メッセージを構築（呼び出し元の情報のみ）
            conversation_message = f"""
私は{caller_user.name}（{caller_user.role}）です。

{message}
"""
            
            # エージェントとの対話実行
            await agent.query(conversation_message)
            
            # ストリーミング応答を収集
            response_parts = []
            
            async for message_response in agent.receive_response():
                if hasattr(message_response, 'content'):
                    for block in message_response.content:
                        if hasattr(block, 'text'):
                            response_parts.append(block.text)
            
            agent_response = ''.join(response_parts)
            
            # セッション更新
            await session_manager.update_session_activity(
                session_id,
                turns_increment=1,
                cost_increment=0.0,
                new_context={
                    "last_message": message[:100] + "..." if len(message) > 100 else message,
                    "last_response": agent_response[:100] + "..." if len(agent_response) > 100 else agent_response,
                    "timestamp": "now"
                }
            )
            
            # 対話ログ記録
            await session_manager.log_agent_activity(
                session_id, 
                caller_user_id, 
                "INFO", 
                f"Conversation with {target_user.name}: {len(message)} chars sent, {len(agent_response)} chars received",
                {
                    "target_user": target_user_id,
                    "message_length": len(message),
                    "response_length": len(agent_response)
                }
            )
            
            return f"💬 **{target_user.name} ({target_user.role})からの返答:**\n\n{agent_response}\n\n---\n📊 セッション: {session_id}"
            
        except Exception as e:
            logger.error(f"Agent conversation failed: {str(e)}")
            return f"❌ 対話エラー: {str(e)}"
    
    @mcp.tool(
        name="list_available_agents",
        description="対話可能なユーザーエージェントの一覧を表示します。各ユーザーの役割と説明を確認できます。"
    )
    async def list_available_agents(caller_user_id: str, ctx: Context) -> str:
        """対話可能なエージェント一覧
        
        Args:
            caller_user_id: 呼び出し元のユーザーID
        """
        try:
            # 呼び出し元ユーザー確認
            caller_user = await database.get_user(caller_user_id)
            if not caller_user:
                raise ValueError(f"ユーザーID '{caller_user_id}' が見つかりません")
            
            # 全ユーザー取得（自分以外）
            all_users = await database.get_all_users()
            available_agents = [user for user in all_users if user.user_id != caller_user_id]
            
            if not available_agents:
                return "🤖 対話可能なエージェントが見つかりません"
            
            # エージェント情報フォーマット
            agent_list = []
            for user in available_agents:
                agent_info = f"""
**{user.name}** (`{user.user_id}`)
- 🏆 役割: {user.role}
- 📝 説明: {user.description if user.description else '未設定'}
"""
                agent_list.append(agent_info.strip())
            
            return "🤖 **対話可能なエージェント一覧**\n\n" + "\n\n---\n\n".join(agent_list) + "\n\n💡 `talk_to_user_agent`ツールでuser_idを指定して対話できます"
            
        except Exception as e:
            logger.error(f"List agents failed: {str(e)}")
            return f"❌ エージェント一覧取得エラー: {str(e)}"
    
    @mcp.tool(
        name="show_conversation_history",
        description="指定したユーザーとの対話履歴・セッション情報を表示します。継続的な対話の文脈確認に使用できます。"
    )
    async def show_conversation_history(
        caller_user_id: str,
        target_user_id: str,
        ctx: Context
    ) -> str:
        """対話履歴表示
        
        Args:
            caller_user_id: 呼び出し元のユーザーID
            target_user_id: 対話相手のユーザーID
        """
        try:
            await ensure_session_init()
            
            # ユーザー確認
            caller_user = await database.get_user(caller_user_id)
            target_user = await database.get_user(target_user_id)
            
            if not caller_user:
                raise ValueError(f"呼び出し元ユーザーID '{caller_user_id}' が見つかりません")
            if not target_user:
                raise ValueError(f"対話相手ユーザーID '{target_user_id}' が見つかりません")
            
            # セッション情報取得
            async with aiosqlite.connect(session_manager.agent_db_path) as db:
                cursor = await db.execute("""
                    SELECT session_id, status, conversation_turns, 
                           created_at, last_active, session_context
                    FROM agent_sessions 
                    WHERE caller_user_id = ? AND target_user_id = ? AND project_path = ?
                    ORDER BY created_at DESC LIMIT 1
                """, (caller_user_id, target_user_id, project_context.project_path))
                
                session_row = await cursor.fetchone()
                
                if not session_row:
                    return f"📝 {caller_user.name} と {target_user.name} の対話履歴が見つかりません"
                
                session_id, status, turns, created_at, last_active, context_json = session_row
                
                # コンテキスト解析
                try:
                    context = json.loads(context_json) if context_json else {}
                except json.JSONDecodeError:
                    context = {}
                
                # ログ履歴取得（最新10件）
                cursor = await db.execute("""
                    SELECT timestamp, log_level, message, metadata
                    FROM agent_logs
                    WHERE session_id = ?
                    ORDER BY timestamp DESC LIMIT 10
                """, (session_id,))
                
                log_rows = await cursor.fetchall()
            
            # 履歴フォーマット
            history_text = f"""
📝 **対話履歴 - {caller_user.name} ↔ {target_user.name}**

🔗 **セッション情報**
- セッションID: {session_id}
- ステータス: {status}
- 総会話ターン: {turns}
- 開始日時: {created_at}
- 最終活動: {last_active}

📋 **最新の対話コンテキスト**
- 最後のメッセージ: {context.get('last_message', '未記録')}
- 最後の応答: {context.get('last_response', '未記録')}

📜 **最近のアクティビティ**
"""
            
            if log_rows:
                for timestamp, level, message, metadata in log_rows[:5]:  # 最新5件
                    history_text += f"- [{timestamp.split('T')[1][:8]}] {message}\n"
            else:
                history_text += "- アクティビティログがありません\n"
            
            history_text += "\n💡 `talk_to_user_agent`で継続的な対話ができます"
            
            return history_text
            
        except Exception as e:
            logger.error(f"Show conversation history failed: {str(e)}")
            return f"❌ 対話履歴取得エラー: {str(e)}"
    
    logger.info("Agent conversation tools registered successfully")
