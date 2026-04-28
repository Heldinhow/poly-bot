"""Generic backend base class for CLI-based agent runtimes."""
import asyncio
import json
import logging
import os
import shutil
from typing import Callable

from agents.runtime.models import (
    AgentBackend,
    ExecutionContext,
    ExecOptions,
    Message,
    MessageType,
    Result,
    Session,
)

logger = logging.getLogger(__name__)


def _default_parser(line: str) -> Message | None:
    """Default parser: treats each line as plain text."""
    if not line.strip():
        return None
    return Message(type=MessageType.TEXT, content=line)


class GenericBackend(AgentBackend):
    """Configurable backend that spawns a CLI and parses stdout line-by-line."""

    def __init__(
        self,
        runtime_name: str,
        cli_command: str,
        parser: Callable[[str], Message | None] | None = None,
        default_args: list[str] | None = None,
    ):
        self._runtime_name = runtime_name
        self._cli_command = cli_command
        self._parser = parser or _default_parser
        self._default_args = default_args or []

    @property
    def name(self) -> str:
        return self._runtime_name

    def is_available(self) -> bool:
        env_var = f"MULTICA_{self._runtime_name.upper().replace('-', '_')}_PATH"
        custom_path = os.environ.get(env_var)
        if custom_path:
            return shutil.which(custom_path) is not None
        return shutil.which(self._cli_command) is not None

    def _build_command(self, prompt: str, opts: ExecOptions) -> list[str]:
        """Build the CLI command. Subclasses can override."""
        cmd = [self._cli_command] + self._default_args + opts.custom_args
        return cmd

    def _build_env(self, opts: ExecOptions) -> dict[str, str]:
        """Build environment variables for the subprocess."""
        env = os.environ.copy()
        env.update(opts.custom_env)
        return env

    async def execute(
        self,
        ctx: ExecutionContext,
        prompt: str,
        opts: ExecOptions,
    ) -> Session:
        session = Session()
        messages_queue: asyncio.Queue[Message | None] = asyncio.Queue()

        cmd = self._build_command(prompt, opts)
        env = self._build_env(opts)
        cwd = opts.cwd

        logger.info(f"[{self.name}] Spawning: {' '.join(cmd)} in {cwd}")

        async def _stream() -> None:
            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=cwd,
                    env=env,
                )

                # Send prompt via stdin
                if proc.stdin:
                    proc.stdin.write(prompt.encode())
                    await proc.stdin.drain()
                    proc.stdin.close()

                # Read stdout line by line
                assert proc.stdout is not None
                raw_output_lines: list[str] = []
                async for line_bytes in proc.stdout:
                    line = line_bytes.decode("utf-8", errors="replace").rstrip("\n")
                    raw_output_lines.append(line)
                    msg = self._parser(line)
                    if msg:
                        await messages_queue.put(msg)

                # Wait for process with timeout
                try:
                    returncode = await asyncio.wait_for(
                        proc.wait(), timeout=opts.timeout.total_seconds()
                    )
                except asyncio.TimeoutError:
                    logger.warning(f"[{self.name}] Timeout after {opts.timeout}")
                    proc.kill()
                    await proc.wait()
                    await messages_queue.put(
                        Message(type=MessageType.ERROR, content="Timeout")
                    )
                    session.result.set_result(
                        Result(error_message="Timeout", raw_output="\n".join(raw_output_lines))
                    )
                    await messages_queue.put(None)
                    return

                # Parse final result from raw output
                raw_output = "\n".join(raw_output_lines)
                result = self._extract_result(raw_output, returncode)
                session.result.set_result(result)

                # Read stderr for logging
                if proc.stderr:
                    stderr_data = await proc.stderr.read()
                    if stderr_data:
                        logger.debug(f"[{self.name}] stderr: {stderr_data.decode()[:500]}")

            except Exception as e:
                logger.error(f"[{self.name}] Execution error: {e}")
                await messages_queue.put(Message(type=MessageType.ERROR, content=str(e)))
                session.result.set_result(Result(error_message=str(e)))
            finally:
                await messages_queue.put(None)

        async def _message_generator() -> None:
            while True:
                msg = await messages_queue.get()
                if msg is None:
                    break
                yield msg

        asyncio.create_task(_stream())
        session.messages = _message_generator()
        return session

    def _extract_result(self, raw_output: str, returncode: int) -> Result:
        """Extract Result from raw output. Subclasses should override for format-specific parsing."""
        if returncode != 0:
            return Result(
                error_message=f"Process exited with code {returncode}",
                raw_output=raw_output,
            )
        # Try to find JSON in the last non-empty lines
        lines = raw_output.strip().splitlines()
        for line in reversed(lines):
            line = line.strip()
            if line.startswith("{") and line.endswith("}"):
                try:
                    data = json.loads(line)
                    return Result(
                        probability=data.get("probability"),
                        confidence=data.get("confidence"),
                        reasoning=data.get("reasoning", ""),
                        sources=data.get("sources", []),
                        raw_output=raw_output,
                    )
                except json.JSONDecodeError:
                    continue
        return Result(raw_output=raw_output)
