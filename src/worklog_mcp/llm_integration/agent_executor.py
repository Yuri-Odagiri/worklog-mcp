"""
AgentExecutor - 多様なLLM実行とプロセス管理
"""

import asyncio
import json
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

from ..models import AgentConfig

logger = logging.getLogger(__name__)


class ProcessManager:
    """プロセス管理クラス（LLMプロバイダー非依存）"""

    def __init__(self):
        self.processes: Dict[str, subprocess.Popen] = {}
        self.process_info: Dict[str, Dict[str, Any]] = {}

    async def start_process(
        self, command: List[str], cwd: str, env: Dict[str, str]
    ) -> str:
        """プロセスを起動し、プロセスIDを返す"""
        process_id = f"llm_agent_{int(time.time() * 1000)}"

        try:
            process = subprocess.Popen(
                command,
                cwd=cwd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                text=True,
                bufsize=1,
            )

            self.processes[process_id] = process
            self.process_info[process_id] = {
                "pid": process.pid,
                "command": command,
                "cwd": cwd,
                "started_at": time.time(),
                "status": "running",
            }

            logger.info(f"プロセス {process_id} を起動: PID {process.pid}")
            return process_id

        except Exception as e:
            logger.error(f"プロセス起動失敗: {e}")
            raise

    async def stop_process(self, process_id: str) -> bool:
        """プロセスを停止"""
        if process_id not in self.processes:
            return False

        try:
            process = self.processes[process_id]
            process.terminate()

            # 優雅な終了を待つ
            try:
                await asyncio.wait_for(
                    asyncio.create_task(self._wait_for_process(process)), timeout=5.0
                )
            except asyncio.TimeoutError:
                # 強制終了
                process.kill()
                await asyncio.create_task(self._wait_for_process(process))

            del self.processes[process_id]
            if process_id in self.process_info:
                self.process_info[process_id]["status"] = "stopped"

            logger.info(f"プロセス {process_id} を停止")
            return True

        except Exception as e:
            logger.error(f"プロセス停止失敗 {process_id}: {e}")
            return False

    async def _wait_for_process(self, process: subprocess.Popen):
        """プロセス終了を非同期で待機"""
        while process.poll() is None:
            await asyncio.sleep(0.1)

    def get_process_status(self, process_id: str) -> Optional[Dict[str, Any]]:
        """プロセス状態を取得"""
        if process_id not in self.process_info:
            return None

        info = self.process_info[process_id].copy()
        if process_id in self.processes:
            process = self.processes[process_id]
            info["is_running"] = process.poll() is None
            info["return_code"] = process.returncode
        else:
            info["is_running"] = False

        return info

    async def send_command(self, process_id: str, command: str) -> Optional[str]:
        """プロセスにコマンドを送信"""
        if process_id not in self.processes:
            return None

        try:
            process = self.processes[process_id]
            if process.poll() is not None:
                return None

            process.stdin.write(command + "\n")
            process.stdin.flush()

            # 基本的な応答読み取り（簡素化）
            # 実際の実装では、より sophisticated な通信プロトコルが必要
            return "Command sent"

        except Exception as e:
            logger.error(f"コマンド送信失敗 {process_id}: {e}")
            return None


class AgentExecutor:
    """LLMエージェント実行管理クラス（マルチプロバイダー対応）"""

    def __init__(self, agent_config: AgentConfig, provider: str = "claude"):
        self.agent_config = agent_config
        self.provider = provider
        self.process_manager = ProcessManager()
        self.temp_dir = None
        self.settings_file = None

    async def start_agent_session(self) -> str:
        """エージェント専用LLMセッション開始"""
        try:
            # 一時ディレクトリ作成
            self.temp_dir = Path(
                tempfile.mkdtemp(
                    prefix=f"{self.provider}_agent_{self.agent_config.agent_id}_"
                )
            )

            # LLM設定ファイル生成
            self.settings_file = await self._create_llm_settings()

            # ワークスペースディレクトリの準備
            workspace_path = self._prepare_workspace()

            # LLM起動コマンド構築
            command = self._build_llm_command()

            # 環境変数設定
            env = self._build_environment()

            # LLMプロセス起動
            llm_process_id = await self.process_manager.start_process(
                command=command, cwd=str(workspace_path), env=env
            )

            logger.info(
                f"{self.provider.upper()} session started for agent {self.agent_config.agent_id}: {llm_process_id}"
            )
            return llm_process_id

        except Exception as e:
            logger.error(f"{self.provider.upper()} session start failed: {e}")
            raise

    async def execute_command(self, command: str, session_id: str) -> Dict[str, Any]:
        """コマンド実行"""
        start_time = time.time()

        try:
            # プロセス状態確認
            status = self.process_manager.get_process_status(session_id)
            if not status or not status.get("is_running"):
                return {
                    "success": False,
                    "error": f"{self.provider.upper()} session is not running",
                    "execution_time": time.time() - start_time,
                }

            # コマンド送信
            result = await self.process_manager.send_command(session_id, command)

            execution_time = time.time() - start_time

            return {
                "success": True,
                "output": result or "",
                "error": None,
                "execution_time": execution_time,
            }

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Command execution failed: {e}")

            return {"success": False, "error": str(e), "execution_time": execution_time}

    async def stop_session(self, session_id: str) -> bool:
        """セッション終了"""
        try:
            # LLMプロセス停止
            stopped = await self.process_manager.stop_process(session_id)

            # 一時ファイルクリーンアップ
            await self._cleanup_temp_files()

            logger.info(f"{self.provider.upper()} session stopped: {session_id}")
            return stopped

        except Exception as e:
            logger.error(f"Session stop failed: {e}")
            return False

    def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """セッション状態取得"""
        return self.process_manager.get_process_status(session_id)

    async def _create_llm_settings(self) -> Path:
        """LLM設定ファイル作成"""
        from ..ai_agents.user_config_converter import UserConfigConverter

        converter = UserConfigConverter()
        settings = converter.generate_llm_settings(self.agent_config, self.provider)

        # ワークスペースパスを設定に埋め込み（Claude固有）
        if (
            self.provider == "claude"
            and "mcp" in settings
            and "servers" in settings["mcp"]
        ):
            for server_name, server_config in settings["mcp"]["servers"].items():
                if "args" in server_config:
                    # --project パラメータを更新
                    args = server_config["args"]
                    for i, arg in enumerate(args):
                        if arg == "--project" and i + 1 < len(args):
                            args[i + 1] = self.agent_config.workspace_path or str(
                                self.temp_dir
                            )
                            break

        settings_file = self.temp_dir / f"{self.provider}_settings.json"
        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)

        return settings_file

    def _prepare_workspace(self) -> Path:
        """ワークスペースディレクトリの準備"""
        if self.agent_config.workspace_path:
            workspace = Path(self.agent_config.workspace_path)
            workspace.mkdir(parents=True, exist_ok=True)
            return workspace
        else:
            # デフォルトワークスペース
            workspace = self.temp_dir / "workspace"
            workspace.mkdir(parents=True, exist_ok=True)
            return workspace

    def _build_llm_command(self) -> List[str]:
        """LLM起動コマンド構築（プロバイダー別）"""
        if self.provider == "claude":
            return self._build_claude_command()
        elif self.provider == "openai":
            return self._build_openai_command()
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def _build_claude_command(self) -> List[str]:
        """Claude起動コマンド構築"""
        command = [
            "claude",
            "--settings",
            str(self.settings_file),
            "--session",
            f"agent_{self.agent_config.agent_id}",
        ]

        return command

    def _build_openai_command(self) -> List[str]:
        """OpenAI起動コマンド構築（将来的な拡張用）"""
        command = [
            "openai-cli",  # 仮想的なコマンド
            "--config",
            str(self.settings_file),
            "--session",
            f"agent_{self.agent_config.agent_id}",
        ]

        return command

    def _build_environment(self) -> Dict[str, str]:
        """環境変数構築"""
        import os

        env = os.environ.copy()

        # エージェント固有の環境変数
        env.update(
            {
                "LLM_AGENT_ID": self.agent_config.agent_id,
                "LLM_USER_ID": self.agent_config.user_id,
                "LLM_PROVIDER": self.provider,
                "LLM_SESSION_MODE": "agent",
            }
        )

        # 旧環境変数との互換性（Claude用）
        if self.provider == "claude":
            env.update(
                {
                    "CLAUDE_AGENT_ID": self.agent_config.agent_id,
                    "CLAUDE_USER_ID": self.agent_config.user_id,
                    "CLAUDE_SESSION_MODE": "agent",
                }
            )

        # ワークスペースパス
        if self.agent_config.workspace_path:
            env["LLM_WORKSPACE"] = self.agent_config.workspace_path
            # Claude互換性
            if self.provider == "claude":
                env["CLAUDE_WORKSPACE"] = self.agent_config.workspace_path

        return env

    async def _cleanup_temp_files(self):
        """一時ファイルのクリーンアップ"""
        try:
            if self.temp_dir and self.temp_dir.exists():
                import shutil

                shutil.rmtree(str(self.temp_dir))
                logger.info(f"Cleaned up temp directory: {self.temp_dir}")
        except Exception as e:
            logger.warning(f"Failed to cleanup temp files: {e}")
