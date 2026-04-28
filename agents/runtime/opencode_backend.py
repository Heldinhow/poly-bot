"""OpenCode backend — spawns `opencode` CLI with json output."""
import json
import logging

from agents.runtime.generic_backend import GenericBackend
from agents.runtime.models import Message, MessageType, Result

logger = logging.getLogger(__name__)


def _parse_opencode_json(line: str) -> Message | None:
    """Parse a line of OpenCode json output.
    
    OpenCode's --format json emits JSON objects, one per line.
    """
    line = line.strip()
    if not line:
        return None
    try:
        data = json.loads(line)
        msg_type = data.get("type", "text")
        content = data.get("content", "")
        metadata = {k: v for k, v in data.items() if k not in ("type", "content")}

        type_map = {
            "text": MessageType.TEXT,
            "thinking": MessageType.THINKING,
            "tool_use": MessageType.TOOL_USE,
            "tool_result": MessageType.TOOL_RESULT,
            "status": MessageType.STATUS,
            "error": MessageType.ERROR,
        }
        mapped_type = type_map.get(msg_type, MessageType.TEXT)
        return Message(type=mapped_type, content=content, metadata=metadata)
    except json.JSONDecodeError:
        return Message(type=MessageType.LOG, content=line)


class OpencodeBackend(GenericBackend):
    """Backend for OpenCode CLI."""

    def __init__(self):
        super().__init__(
            runtime_name="opencode",
            cli_command="opencode",
            parser=_parse_opencode_json,
            default_args=["run", "--format", "json"],
        )

    def _build_command(self, prompt: str, opts) -> list[str]:
        """Build OpenCode command."""
        cmd = [self._cli_command] + self._default_args
        if opts.model:
            cmd.extend(["--model", opts.model])
        cmd.extend(opts.custom_args)
        # OpenCode reads prompt from stdin via run command
        return cmd

    def _extract_result(self, raw_output: str, returncode: int) -> Result:
        """Extract Result from OpenCode output."""
        if returncode != 0:
            return Result(
                error_message=f"OpenCode exited with code {returncode}",
                raw_output=raw_output,
            )
        return super()._extract_result(raw_output, returncode)
