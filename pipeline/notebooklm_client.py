"""
NotebookLM MCP Client
=====================
Python wrapper that communicates with the notebooklm-mcp TypeScript server
via MCP stdio JSON-RPC protocol.

Uses subprocess to launch `npx notebooklm-mcp` and sends/receives
JSON-RPC messages over stdin/stdout.
"""

import json
import logging
import os
import subprocess
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

QUOTA_FILE_DIR = Path.home() / ".config" / "ai-whisper"
QUOTA_FILE = QUOTA_FILE_DIR / "notebooklm_quota.json"


class NotebookLMError(Exception):
    """Base error for NotebookLM operations."""


class RateLimitError(NotebookLMError):
    """Raised when the daily quota is exhausted."""


class AuthenticationError(NotebookLMError):
    """Raised when authentication is missing or expired."""


class NotebookLMClient:
    """Communicates with notebooklm-mcp via MCP stdio transport (JSON-RPC).

    Each method call starts a fresh subprocess, sends a JSON-RPC request,
    and reads the response. This is simpler than maintaining a persistent
    connection and aligns with the MCP server's design.
    """

    def __init__(
        self,
        daily_quota: int = 50,
        npx_command: str = "npx",
        mcp_package: str = "notebooklm-mcp@latest",
        login_email: str = "",
    ) -> None:
        self.daily_quota = daily_quota
        self.npx_command = npx_command
        self.mcp_package = mcp_package
        self.login_email = login_email
        self._request_id = 0

    # ------------------------------------------------------------------
    # Quota tracking (local file-based)
    # ------------------------------------------------------------------

    def _load_quota(self) -> dict[str, Any]:
        """Load quota tracking data from local JSON file."""
        if QUOTA_FILE.exists():
            try:
                return json.loads(QUOTA_FILE.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        return {"date": str(date.today()), "used": 0}

    def _save_quota(self, data: dict[str, Any]) -> None:
        """Persist quota tracking data."""
        QUOTA_FILE_DIR.mkdir(parents=True, exist_ok=True)
        QUOTA_FILE.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def increment_quota(self) -> int:
        """Increment daily query count and return the new count."""
        data = self._load_quota()
        today = str(date.today())
        if data.get("date") != today:
            data = {"date": today, "used": 0}
        data["used"] += 1
        self._save_quota(data)
        return data["used"]

    def get_remaining_quota(self) -> int:
        """Return the number of queries remaining today."""
        data = self._load_quota()
        today = str(date.today())
        if data.get("date") != today:
            return self.daily_quota
        return max(0, self.daily_quota - data.get("used", 0))

    def get_quota_info(self) -> dict[str, Any]:
        """Return full quota status."""
        data = self._load_quota()
        today = str(date.today())
        if data.get("date") != today:
            return {"date": today, "used": 0, "remaining": self.daily_quota, "limit": self.daily_quota}
        used = data.get("used", 0)
        return {"date": today, "used": used, "remaining": max(0, self.daily_quota - used), "limit": self.daily_quota}

    # ------------------------------------------------------------------
    # MCP JSON-RPC communication
    # ------------------------------------------------------------------

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def _build_jsonrpc(self, method: str, params: Optional[dict[str, Any]] = None) -> str:
        """Build a JSON-RPC 2.0 request message."""
        msg: dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
        }
        if params is not None:
            msg["params"] = params
        return json.dumps(msg)

    def _call_mcp(self, method: str, params: Optional[dict[str, Any]] = None, timeout: int = 180) -> dict[str, Any]:
        """Launch npx notebooklm-mcp, send a JSON-RPC request, read the response.

        The MCP stdio transport expects:
         - Client sends "initialize" first
         - Then "tools/call" with the tool name & arguments

        Returns the parsed result dict from the MCP response.
        """
        cmd = [self.npx_command, "-y", self.mcp_package]

        try:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env={
                    **os.environ,
                    "NODE_NO_WARNINGS": "1",
                    "LOGIN_EMAIL": self.login_email
                },
            )
        except FileNotFoundError:
            raise NotebookLMError(
                f"Cannot find '{self.npx_command}'. Ensure Node.js is installed."
            )

        try:
            # Step 1: Send initialize request
            init_msg = self._build_jsonrpc("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "ai-whisper", "version": "1.0.0"},
            })
            proc.stdin.write(init_msg + "\n")
            proc.stdin.flush()

            # Read initialize response
            init_response = self._read_response(proc, timeout=30)
            logger.debug(f"MCP initialize response: {init_response}")

            # Send initialized notification
            initialized_msg = json.dumps({
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
            })
            proc.stdin.write(initialized_msg + "\n")
            proc.stdin.flush()

            # Step 2: Send the actual tool call
            tool_msg = self._build_jsonrpc("tools/call", {
                "name": method,
                "arguments": params or {},
            })
            proc.stdin.write(tool_msg + "\n")
            proc.stdin.flush()

            # Read tool response
            response = self._read_response(proc, timeout=timeout)
            return response

        except subprocess.TimeoutExpired:
            proc.kill()
            raise NotebookLMError(f"MCP call timed out after {timeout}s")
        finally:
            proc.stdin.close()
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

    def _read_response(self, proc: subprocess.Popen, timeout: int = 60) -> dict[str, Any]:
        """Read a single JSON-RPC response line from the process stdout."""
        start = time.time()
        while time.time() - start < timeout:
            if proc.poll() is not None:
                stderr_output = proc.stderr.read() if proc.stderr else ""
                raise NotebookLMError(
                    f"MCP process exited unexpectedly (code {proc.returncode}). "
                    f"Stderr: {stderr_output[:500]}"
                )

            line = proc.stdout.readline().strip()
            if not line:
                time.sleep(0.1)
                continue

            try:
                data = json.loads(line)
                if "id" in data or "method" in data:
                    return data
            except json.JSONDecodeError:
                logger.debug(f"Skipping non-JSON line: {line[:200]}")
                continue

        raise NotebookLMError(f"Timeout waiting for MCP response ({timeout}s)")

    # ------------------------------------------------------------------
    # Public API methods
    # ------------------------------------------------------------------

    def ask_question(
        self,
        question: str,
        notebook_url: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Ask a question to NotebookLM.

        Args:
            question: The question to ask.
            notebook_url: Optional notebook URL to target.
            session_id: Optional session ID for follow-up questions.

        Returns:
            Dict with 'answer', 'session_id', and metadata.

        Raises:
            RateLimitError: If daily quota is exhausted.
            AuthenticationError: If not authenticated.
            NotebookLMError: For other errors.
        """
        remaining = self.get_remaining_quota()
        if remaining <= 0:
            raise RateLimitError(
                f"Daily quota exhausted ({self.daily_quota} queries/day). "
                f"Resets tomorrow."
            )

        params: dict[str, Any] = {"question": question}
        if notebook_url:
            params["notebook_url"] = notebook_url
        if session_id:
            params["session_id"] = session_id

        result = self._call_mcp("ask_question", params, timeout=180)

        # Parse MCP response
        if "error" in result:
            error_msg = result["error"].get("message", str(result["error"]))
            if "rate limit" in error_msg.lower():
                raise RateLimitError(error_msg)
            if "auth" in error_msg.lower() or "login" in error_msg.lower():
                raise AuthenticationError(error_msg)
            raise NotebookLMError(error_msg)

        # Increment quota on success
        self.increment_quota()

        # Extract answer from MCP tool result
        tool_result = result.get("result", {})
        content_list = tool_result.get("content", [])
        answer_text = ""
        for content_item in content_list:
            if content_item.get("type") == "text":
                answer_text = content_item.get("text", "")
                break

        # Try to parse embedded JSON
        parsed: dict[str, Any] = {"raw_answer": answer_text}
        try:
            embedded = json.loads(answer_text)
            if isinstance(embedded, dict):
                parsed = embedded
        except (json.JSONDecodeError, TypeError):
            pass

        return {
            "answer": parsed.get("answer", parsed.get("raw_answer", answer_text)),
            "session_id": parsed.get("session_id"),
            "notebook_url": parsed.get("notebook_url"),
            "success": parsed.get("status") == "success" or bool(answer_text),
        }

    def generate_studio_output(
        self,
        output_type: str,
        session_id: Optional[str] = None,
        notebook_url: Optional[str] = None,
        show_browser: bool = False,
    ) -> str:
        """Generate specified output in the Studio tab.

        Args:
            output_type: One of 'audio', 'mindmap', 'presentation', 'studyguide'.
            session_id: Optional session ID to reuse.
            notebook_url: Optional notebook URL if starting new session.
            show_browser: Whether to show the browser window.

        Returns:
            Status message from the server.
        """
        # Increment quota
        self.increment_quota()

        params: dict[str, Any] = {
            "type": output_type,
            "show_browser": show_browser,
        }
        if session_id:
            params["session_id"] = session_id
        if notebook_url:
            params["notebook_url"] = notebook_url

        result = self._call_mcp("generate_studio_output", params, timeout=600)  # Long timeout for audio

        if "error" in result:
            error_msg = result["error"].get("message", str(result["error"]))
            if "rate limit" in error_msg.lower():
                raise RateLimitError(error_msg)
            raise NotebookLMError(f"Failed to generate studio output: {error_msg}")

        tool_result = result.get("result", {})
        content_list = tool_result.get("content", [])
        answer_text = ""
        for content_item in content_list:
            if content_item.get("type") == "text":
                answer_text = content_item.get("text", "")
                break

        try:
            data = json.loads(answer_text)
            return data.get("message", answer_text)
        except (json.JSONDecodeError, TypeError):
            return answer_text

    def get_health(self) -> dict[str, Any]:
        """Check the health/auth status of the MCP server."""
        result = self._call_mcp("get_health", timeout=30)
        tool_result = result.get("result", {})
        content_list = tool_result.get("content", [])
        for content_item in content_list:
            if content_item.get("type") == "text":
                try:
                    return json.loads(content_item["text"])
                except (json.JSONDecodeError, TypeError):
                    return {"raw": content_item.get("text", "")}
        return {"status": "unknown"}

    def list_notebooks(self) -> list[dict[str, Any]]:
        """List all notebooks in the library."""
        result = self._call_mcp("list_notebooks", timeout=30)
        tool_result = result.get("result", {})
        content_list = tool_result.get("content", [])
        for content_item in content_list:
            if content_item.get("type") == "text":
                try:
                    data = json.loads(content_item["text"])
                    return data.get("notebooks", [])
                except (json.JSONDecodeError, TypeError):
                    pass
        return []
