"""
SessionManager - LLMエージェントセッション管理（マルチプロバイダー対応）
"""

import asyncio
import time
from typing import Dict, Any, Optional, List
import logging

from ..models import AgentSession, SessionStatus, User, ConversationHistory, MessageRole
from .agent_executor import AgentExecutor

logger = logging.getLogger(__name__)


class SessionManager:
    """LLMエージェントセッション管理クラス"""

    def __init__(self):
        self.active_sessions: Dict[str, AgentSession] = {}
        self.session_executors: Dict[str, AgentExecutor] = {}
        self.session_locks: Dict[str, asyncio.Lock] = {}
        self.conversation_histories: Dict[
            str, ConversationHistory
        ] = {}  # セッションID -> 会話履歴
        self.cleanup_task: Optional[asyncio.Task] = None

    async def start(self):
        """SessionManager開始"""
        # 定期クリーンアップタスクを開始
        self.cleanup_task = asyncio.create_task(self._periodic_cleanup())
        logger.info("SessionManager started with periodic cleanup")

    async def stop(self):
        """SessionManager停止"""
        # 全セッション停止
        await self.stop_all_sessions()

        # クリーンアップタスク停止
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass

        logger.info("SessionManager stopped")

    async def create_agent_session(
        self, user: User, workspace_path: str = "", provider: str = "claude"
    ) -> str:
        """エージェント専用セッション作成"""
        agent_id = f"agent_{user.user_id}"

        # 既存セッションの確認
        existing_session = await self.get_user_active_session(user.user_id)
        if existing_session:
            logger.warning(
                f"User {user.user_id} already has active session: {existing_session.session_id}"
            )
            return existing_session.session_id

        try:
            # ユーザー設定からエージェント設定を作成
            from ..ai_agents.user_config_converter import UserConfigConverter

            converter = UserConfigConverter()
            agent_config = converter.convert_user_to_agent_config(
                user, workspace_path, provider
            )

            # AgentExecutor作成
            executor = AgentExecutor(agent_config, provider)

            # セッション作成
            session = AgentSession(
                agent_id=agent_id,
                user_id=user.user_id,
                workspace_path=workspace_path,
                status=SessionStatus.STARTING,
            )

            # セッション登録
            self.active_sessions[session.session_id] = session
            self.session_executors[session.session_id] = executor
            self.session_locks[session.session_id] = asyncio.Lock()

            # 会話履歴初期化
            self.conversation_histories[session.session_id] = ConversationHistory(
                session_id=session.session_id
            )

            # LLMセッション開始
            llm_process_id = await executor.start_agent_session()

            # セッション情報更新
            session.claude_process_id = llm_process_id
            session.status = SessionStatus.ACTIVE
            session.last_activity = time.time()

            logger.info(
                f"Agent session created: {session.session_id} for user {user.user_id} with {provider}"
            )
            return session.session_id

        except Exception as e:
            # エラー時はセッションをクリーンアップ
            if session.session_id in self.active_sessions:
                await self._cleanup_session(session.session_id)

            logger.error(f"Failed to create agent session for user {user.user_id}: {e}")
            raise

    async def execute_with_agent(self, session_id: str, command: str) -> Dict[str, Any]:
        """指定したエージェントでコマンド実行"""
        if session_id not in self.active_sessions:
            return {"success": False, "error": f"Session {session_id} not found"}

        session = self.active_sessions[session_id]
        executor = self.session_executors[session_id]
        lock = self.session_locks[session_id]

        async with lock:
            try:
                # セッション状態確認
                if session.status != SessionStatus.ACTIVE:
                    return {
                        "success": False,
                        "error": f"Session {session_id} is not active (status: {session.status.value})",
                    }

                # コマンド実行
                result = await executor.execute_command(
                    command, session.claude_process_id
                )

                # 最終アクティビティ時刻更新
                session.last_activity = time.time()

                logger.info(
                    f"Command executed in session {session_id}: {command[:50]}..."
                )
                return result

            except Exception as e:
                logger.error(f"Command execution failed in session {session_id}: {e}")

                # エラー状態に設定
                session.status = SessionStatus.ERROR

                return {"success": False, "error": str(e)}

    async def send_message_to_agent(
        self, session_id: str, message: str
    ) -> Dict[str, Any]:
        """エージェントに会話メッセージを送信"""
        if session_id not in self.active_sessions:
            return {"success": False, "error": f"Session {session_id} not found"}

        session = self.active_sessions[session_id]
        executor = self.session_executors[session_id]
        lock = self.session_locks[session_id]
        conversation_history = self.conversation_histories.get(session_id)

        async with lock:
            try:
                # セッション状態確認
                if session.status != SessionStatus.ACTIVE:
                    return {
                        "success": False,
                        "error": f"Session {session_id} is not active (status: {session.status.value})",
                    }

                # ユーザーメッセージを履歴に追加
                if conversation_history:
                    conversation_history.add_message(MessageRole.USER, message)

                # メッセージ送信
                result = await executor.send_message(
                    message, session.claude_process_id, conversation_history
                )

                # 応答を履歴に追加
                if result["success"] and conversation_history:
                    conversation_history.add_message(
                        MessageRole.ASSISTANT,
                        result.get("response", ""),
                        metadata=result.get("metadata", {}),
                    )

                # 最終アクティビティ時刻更新
                session.last_activity = time.time()

                logger.info(f"Message sent to session {session_id}: {message[:50]}...")
                return result

            except Exception as e:
                logger.error(f"Message sending failed in session {session_id}: {e}")

                # エラー状態に設定
                session.status = SessionStatus.ERROR

                return {"success": False, "error": str(e)}

    async def get_conversation_history(
        self, session_id: str, limit: int = 50
    ) -> Optional[List[Dict[str, Any]]]:
        """会話履歴を取得"""
        if session_id not in self.conversation_histories:
            return None

        conversation_history = self.conversation_histories[session_id]
        recent_messages = conversation_history.get_recent_messages(limit)

        return [
            {
                "message_id": msg.message_id,
                "role": msg.role.value,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
                "metadata": msg.metadata,
            }
            for msg in recent_messages
        ]

    async def clear_conversation_history(self, session_id: str) -> bool:
        """会話履歴をクリア"""
        if session_id not in self.conversation_histories:
            return False

        self.conversation_histories[session_id].clear_history()
        logger.info(f"Conversation history cleared for session {session_id}")
        return True

    async def stop_agent_session(self, session_id: str) -> bool:
        """エージェントセッション停止"""
        if session_id not in self.active_sessions:
            return False

        session = self.active_sessions[session_id]
        executor = self.session_executors[session_id]
        lock = self.session_locks[session_id]

        async with lock:
            try:
                session.status = SessionStatus.STOPPING

                # LLMセッション停止
                stopped = await executor.stop_session(session.claude_process_id)

                # セッションクリーンアップ
                await self._cleanup_session(session_id)

                logger.info(f"Agent session stopped: {session_id}")
                return stopped

            except Exception as e:
                logger.error(f"Failed to stop session {session_id}: {e}")
                return False

    async def stop_all_sessions(self):
        """全エージェントセッション停止"""
        session_ids = list(self.active_sessions.keys())

        for session_id in session_ids:
            try:
                await self.stop_agent_session(session_id)
            except Exception as e:
                logger.error(f"Failed to stop session {session_id}: {e}")

        logger.info(f"Stopped {len(session_ids)} agent sessions")

    async def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """セッション状態取得"""
        if session_id not in self.active_sessions:
            return None

        session = self.active_sessions[session_id]
        executor = self.session_executors[session_id]

        # プロセス状態取得
        process_status = executor.get_session_status(session.claude_process_id)

        return {
            "session_id": session.session_id,
            "agent_id": session.agent_id,
            "user_id": session.user_id,
            "status": session.status.value,
            "created_at": session.created_at.isoformat(),
            "last_activity": session.last_activity.isoformat(),
            "workspace_path": session.workspace_path,
            "process_status": process_status,
        }

    async def list_active_sessions(
        self, user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """アクティブセッション一覧取得"""
        sessions = []

        for session_id, session in self.active_sessions.items():
            if user_id and session.user_id != user_id:
                continue

            status_info = await self.get_session_status(session_id)
            if status_info:
                sessions.append(status_info)

        return sessions

    async def get_user_active_session(self, user_id: str) -> Optional[AgentSession]:
        """ユーザーのアクティブセッション取得"""
        for session in self.active_sessions.values():
            if session.user_id == user_id and session.status == SessionStatus.ACTIVE:
                return session
        return None

    async def _cleanup_session(self, session_id: str):
        """セッションクリーンアップ"""
        if session_id in self.active_sessions:
            self.active_sessions[session_id].status = SessionStatus.STOPPED
            del self.active_sessions[session_id]

        if session_id in self.session_executors:
            del self.session_executors[session_id]

        if session_id in self.session_locks:
            del self.session_locks[session_id]

        if session_id in self.conversation_histories:
            del self.conversation_histories[session_id]

    async def _periodic_cleanup(self):
        """定期的な非アクティブセッションクリーンアップ"""
        while True:
            try:
                await asyncio.sleep(300)  # 5分ごと
                await self.cleanup_inactive_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Periodic cleanup error: {e}")

    async def cleanup_inactive_sessions(self, idle_timeout: int = 1800):
        """非アクティブセッションクリーンアップ"""
        current_time = time.time()
        inactive_sessions = []

        for session_id, session in self.active_sessions.items():
            # 最終アクティビティから指定時間経過したセッション
            if current_time - session.last_activity.timestamp() > idle_timeout:
                inactive_sessions.append(session_id)

        for session_id in inactive_sessions:
            try:
                logger.info(f"Cleaning up inactive session: {session_id}")
                await self.stop_agent_session(session_id)
            except Exception as e:
                logger.error(f"Failed to cleanup session {session_id}: {e}")

        if inactive_sessions:
            logger.info(f"Cleaned up {len(inactive_sessions)} inactive sessions")

    def get_session_count(self) -> Dict[str, int]:
        """セッション数統計"""
        status_counts = {}
        for session in self.active_sessions.values():
            status = session.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        return {"total": len(self.active_sessions), "by_status": status_counts}
