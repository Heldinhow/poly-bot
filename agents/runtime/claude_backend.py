"""Claude Code backend — spawns `claude` CLI with stream-json output."""
import json
import logging

from agents.runtime.generic_backend import GenericBackend
from agents.runtime.models import Message, MessageType, Result

logger = logging.getLogger(__name__)


def _parse_claude_stream_json(line: str) -> Message | None:
    """Parse a line of Claude Code stream-json output.
    
    Claude's stream-json format emits JSON objects, one per line.
    Common types: "text", "thinking", "tool_use", "tool_result", "status".
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
            "log": MessageType.LOG,
        }
        mapped_type = type_map.get(msg_type, MessageType.TEXT)
        return Message(type=mapped_type, content=content, metadata=metadata)
    except json.JSONDecodeError:
        # Not JSON — treat as plain text log
        return Message(type=MessageType.LOG, content=line)


class ClaudeBackend(GenericBackend):
    """Backend for Anthropic's Claude Code CLI."""

    def __init__(self):
        super().__init__(
            runtime_name="claude",
            cli_command="claude",
            parser=_parse_claude_stream_json,
            default_args=["-p", "--output-format", "stream-json"],
        )

    def _build_command(self, prompt: str, opts) -> list[str]:
        """Build Claude Code command with optional model override."""
        cmd = [self._cli_command] + self._default_args
        if opts.model:
            cmd.extend(["--model", opts.model])
        cmd.extend(opts.custom_args)
        # Claude -p reads prompt from stdin
        return cmd

    def _extract_result(self, raw_output: str, returncode: int) -> Result:
        """Extract Result from Claude Code output.
        
        Claude's stream-json output may have the final JSON result as the last
        'text' message, or as a standalone JSON block.
        """
        if returncode != 0:
            return Result(
                error_message=f"Claude exited with code {returncode}",
                raw_output=raw_output,
            )

        # Try to find the final JSON result in stream-json text messages
        lines = raw_output.strip().splitlines()
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                # If it's a stream-json wrapper, unwrap the content
                if isinstance(data, dict) and "content" in data:
                    content = data["content"]
                    if isinstance(content, str):
                        content = content.strip()
                        if content.startswith("{") and content.endswith("}"):
                            data = json.loads(content)
                        else:
                            continue
                    elif isinstance(content, dict):
                        data = content
                    else:
                        continue

                if "probability" in data or "confidence" in data:
                    return Result(
                        probability=data.get("probability"),
                        confidence=data.get("confidence"),
                        reasoning=data.get("reasoning", ""),
                        sources=data.get("sources", []),
                        raw_output=raw_output,
                        input_tokens=data.get("input_tokens", 0),
                        output_tokens=data.get("output_tokens", 0),
                    )
            except json.JSONDecodeError:
                continue

        # Fallback: plain JSON in output
        return super()._extract_result(raw_output, returncode)
