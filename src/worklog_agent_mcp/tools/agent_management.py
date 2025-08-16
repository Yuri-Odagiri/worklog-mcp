"""Agent管理MCPツール"""

import logging
from typing import Dict, Any, Optional

from mcp.server.fastmcp import FastMCP
from worklog_mcp.database import Database
from worklog_mcp.project_context import ProjectContext
from worklog_mcp.models import AgentSession, AgentConfig, SessionStatus, AgentExecutionResult
from worklog_mcp.llm_integration import SessionManager, mcp_config_generator
from worklog_mcp.ai_agents import PersonalityEngine, UserConfigConverter

logger = logging.getLogger(__name__)


class AgentManager:
    """Agent管理クラス"""
    
    def __init__(self, database: Database, project_context: ProjectContext, user_id: Optional[str] = None):
        self.database = database
        self.project_context = project_context
        self.user_id = user_id
        self.session_manager = SessionManager()
        self.personality_engine = PersonalityEngine()
        self.user_converter = UserConfigConverter()
        
    async def start_claude_agent(
        self,
        user_id: str,
        agent_id: Optional[str] = None,
        workspace_path: Optional[str] = None,
        custom_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Claude Agentセッションを開始"""
        try:
            # ユーザー情報を取得
            user = await self.database.get_user(user_id)
            if not user:
                return {
                    "success": False,
                    "error": f"ユーザー '{user_id}' が見つかりません"
                }
            
            # エージェントIDが指定されていない場合はuser_idを使用
            if not agent_id:
                agent_id = user_id
            
            # ワークスペースパスの設定
            if not workspace_path:
                workspace_path = self.project_context.project_path
            
            # エージェント設定を生成
            agent_config = await self._create_agent_config(
                user=user,
                agent_id=agent_id,
                workspace_path=workspace_path,
                custom_prompt=custom_prompt
            )
            
            # セッションを作成
            session = AgentSession(
                agent_id=agent_id,
                user_id=user_id,
                workspace_path=workspace_path,
                status=SessionStatus.STARTING
            )
            
            # データベースに保存
            await self.database.create_agent_session(session)
            
            # MCP設定ファイルを生成
            mcp_config_path = await mcp_config_generator.generate_agent_config(
                session=session,
                agent_config=agent_config,
                project_path=self.project_context.project_path
            )
            
            # 設定パスを更新
            session.mcp_config_path = mcp_config_path
            await self.database.update_agent_session_status(session.session_id, SessionStatus.STARTING)
            
            # セッションマネージャーに登録
            await self.session_manager.create_session(session, agent_config)
            
            # Claudeプロセスを起動（現在は仮実装）
            process_id = f"claude_process_{session.session_id}"
            
            # プロセスIDを更新
            await self.database.update_agent_session_process_id(session.session_id, str(process_id))
            await self.database.update_agent_session_status(session.session_id, SessionStatus.ACTIVE)
            
            logger.info(f"Claude Agentセッションを開始しました: {session.session_id}")
            
            return {
                "success": True,
                "session_id": session.session_id,
                "agent_id": agent_id,
                "user_id": user_id,
                "process_id": process_id,
                "workspace_path": workspace_path,
                "mcp_config_path": mcp_config_path,
                "status": SessionStatus.ACTIVE.value
            }
            
        except Exception as e:
            logger.error(f"Claude Agent起動に失敗: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def stop_agent_session(
        self,
        session_id: str,
        force: bool = False
    ) -> Dict[str, Any]:
        """エージェントセッションを停止"""
        try:
            # セッションの確認
            session = await self.database.get_agent_session(session_id)
            if not session:
                return {
                    "success": False,
                    "error": f"セッション '{session_id}' が見つかりません"
                }
            
            # 停止処理を開始
            await self.database.update_agent_session_status(session_id, SessionStatus.STOPPING)
            
            # Claudeプロセスを停止（現在は仮実装）
            stop_result = True
            
            # セッションマネージャーからセッションを削除
            await self.session_manager.remove_session(session_id)
            
            # MCP設定ファイルをクリーンアップ
            if session.mcp_config_path:
                await mcp_config_generator.cleanup_config(session_id)
            
            # セッション状態を更新
            await self.database.update_agent_session_status(session_id, SessionStatus.STOPPED)
            
            logger.info(f"Claude Agentセッションを停止しました: {session_id}")
            
            return {
                "success": True,
                "session_id": session_id,
                "stop_result": stop_result,
                "status": SessionStatus.STOPPED.value
            }
            
        except Exception as e:
            logger.error(f"Claude Agent停止に失敗: {e}")
            try:
                await self.database.update_agent_session_status(session_id, SessionStatus.ERROR)
            except Exception:
                pass
            
            return {
                "success": False,
                "error": str(e)
            }
    
    async def list_agent_sessions(
        self,
        user_id: Optional[str] = None,
        status_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """エージェントセッション一覧を取得"""
        try:
            status = None
            if status_filter:
                try:
                    status = SessionStatus(status_filter)
                except ValueError:
                    return {
                        "success": False,
                        "error": f"無効なステータス: {status_filter}"
                    }
            
            sessions = await self.database.list_agent_sessions(user_id=user_id, status=status)
            
            session_list = []
            for session in sessions:
                session_info = {
                    "session_id": session.session_id,
                    "agent_id": session.agent_id,
                    "user_id": session.user_id,
                    "claude_process_id": session.claude_process_id,
                    "workspace_path": session.workspace_path,
                    "status": session.status.value,
                    "created_at": session.created_at.isoformat(),
                    "last_activity": session.last_activity.isoformat()
                }
                
                # ユーザー情報を追加
                user = await self.database.get_user(session.user_id)
                if user:
                    session_info["user_name"] = user.name
                    session_info["user_role"] = user.role
                
                session_list.append(session_info)
            
            return {
                "success": True,
                "sessions": session_list,
                "total_count": len(session_list)
            }
            
        except Exception as e:
            logger.error(f"セッション一覧取得に失敗: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def execute_with_agent(
        self,
        session_id: str,
        command: str,
        timeout: int = 60
    ) -> Dict[str, Any]:
        """エージェントでコマンドを実行"""
        try:
            # セッションの確認
            session = await self.database.get_agent_session(session_id)
            if not session:
                return {
                    "success": False,
                    "error": f"セッション '{session_id}' が見つかりません"
                }
            
            if session.status != SessionStatus.ACTIVE:
                return {
                    "success": False,
                    "error": f"セッションが非アクティブです: {session.status.value}"
                }
            
            # コマンドを実行（現在は仮実装）
            from datetime import datetime
            start_time = datetime.now()
            
            # 仮の実行結果
            result = {
                "success": True,
                "output": f"Command executed: {command}",
                "error": None
            }
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # 実行結果を保存
            execution_result = AgentExecutionResult(
                session_id=session_id,
                command=command,
                output=result.get("output", ""),
                error=result.get("error"),
                execution_time=execution_time
            )
            
            await self.database.save_execution_result(execution_result)
            
            # セッションの最終活動時刻を更新
            await self.database.update_agent_session_status(session_id, SessionStatus.ACTIVE)
            
            return {
                "success": result.get("success", False),
                "output": result.get("output", ""),
                "error": result.get("error"),
                "execution_time": execution_time,
                "session_id": session_id
            }
            
        except Exception as e:
            logger.error(f"エージェントコマンド実行に失敗: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """セッション状態を取得"""
        try:
            session = await self.database.get_agent_session(session_id)
            if not session:
                return {
                    "success": False,
                    "error": f"セッション '{session_id}' が見つかりません"
                }
            
            # ユーザー情報を取得
            user = await self.database.get_user(session.user_id)
            
            # 実行履歴を取得（最新5件）
            execution_history = await self.database.get_execution_history(session_id, limit=5)
            
            return {
                "success": True,
                "session": {
                    "session_id": session.session_id,
                    "agent_id": session.agent_id,
                    "user_id": session.user_id,
                    "user_name": user.name if user else "Unknown",
                    "claude_process_id": session.claude_process_id,
                    "workspace_path": session.workspace_path,
                    "status": session.status.value,
                    "created_at": session.created_at.isoformat(),
                    "last_activity": session.last_activity.isoformat()
                },
                "recent_executions": [
                    {
                        "command": exec_result.command,
                        "execution_time": exec_result.execution_time,
                        "timestamp": exec_result.timestamp.isoformat(),
                        "has_error": bool(exec_result.error)
                    }
                    for exec_result in execution_history
                ]
            }
            
        except Exception as e:
            logger.error(f"セッション状態取得に失敗: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _create_agent_config(
        self,
        user: Any,
        agent_id: str,
        workspace_path: str,
        custom_prompt: Optional[str] = None
    ) -> AgentConfig:
        """エージェント設定を作成"""
        
        # ユーザー設定をエージェント設定に変換
        agent_settings = self.user_converter.convert_user_to_agent_config(user)
        
        # 人格プロンプトを生成
        system_prompt = self.personality_engine.generate_system_prompt(
            personality=user.personality,
            role=user.role,
            appearance=user.appearance,
            custom_instructions=custom_prompt or user.instruction
        )
        
        # MCP サーバー設定
        mcp_servers = {}
        if user.mcp:
            try:
                import json
                mcp_servers = json.loads(user.mcp)
            except Exception:
                # デフォルトのworklog-mcp設定
                mcp_servers = {
                    "worklog-mcp": {
                        "command": "uv",
                        "args": ["run", "python", "-m", "worklog_mcp", "--project", workspace_path, "--transport", "stdio"]
                    }
                }
        
        # 許可ツール設定
        allowed_tools = []
        if user.tools:
            allowed_tools = user.tools.split(",")
        
        return AgentConfig(
            agent_id=agent_id,
            claude_model=user.model or "claude-3-sonnet-20240229",
            system_prompt=system_prompt,
            allowed_tools=allowed_tools,
            mcp_servers=mcp_servers,
            session_config=agent_settings,
            user_id=user.user_id,
            workspace_path=workspace_path
        )


def register_agent_tools(server: FastMCP, database: Database, project_context: ProjectContext, user_id: Optional[str] = None):
    """Agent管理ツールをMCPサーバーに登録"""
    
    agent_manager = AgentManager(database, project_context, user_id)
    
    @server.tool()
    async def start_claude_agent(
        user_id: str,
        agent_id: str = None,
        workspace_path: str = None,
        custom_prompt: str = None
    ) -> dict:
        """Claude Agentセッションを開始"""
        return await agent_manager.start_claude_agent(
            user_id=user_id,
            agent_id=agent_id,
            workspace_path=workspace_path,
            custom_prompt=custom_prompt
        )
    
    @server.tool()
    async def stop_agent_session(session_id: str, force: bool = False) -> dict:
        """エージェントセッションを停止"""
        return await agent_manager.stop_agent_session(session_id=session_id, force=force)
    
    @server.tool()
    async def list_agent_sessions(user_id: str = None, status_filter: str = None) -> dict:
        """エージェントセッション一覧を取得"""
        return await agent_manager.list_agent_sessions(
            user_id=user_id, 
            status_filter=status_filter
        )
    
    @server.tool()
    async def execute_with_agent(session_id: str, command: str, timeout: int = 60) -> dict:
        """エージェントでコマンドを実行"""
        return await agent_manager.execute_with_agent(
            session_id=session_id,
            command=command,
            timeout=timeout
        )
    
    @server.tool()
    async def get_session_status(session_id: str) -> dict:
        """セッション状態を取得"""
        return await agent_manager.get_session_status(session_id=session_id)
    
    logger.info("Agent管理ツールを登録しました")