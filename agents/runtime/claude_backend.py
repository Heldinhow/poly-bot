"""Claude Code backend — spawns `claude` CLI with stream-json output."""
import json
import logging
import re

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
            default_args=["-p", "--output-format", "stream-json", "--verbose"],
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
        """Extract Result from Claude Code stream-json output.

        Claude's stream-json format:
        - Lines are JSON objects with "type" field
        - The final result is in a line with type="result" and "result" field
        - The result text may contain markdown code blocks with JSON
        """
        if returncode != 0:
            return Result(
                error_message=f"Claude exited with code {returncode}",
                raw_output=raw_output,
            )

        lines = raw_output.strip().splitlines()

        # Strategy 1: Find type="result" line and extract "result" field
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                if isinstance(data, dict) and data.get("type") == "result":
                    result_text = data.get("result", "")
                    parsed = self._parse_json_from_text(result_text)
                    if parsed and ("probability" in parsed or "confidence" in parsed):
                        usage = data.get("usage", {})
                        return Result(
                            probability=parsed.get("probability"),
                            confidence=parsed.get("confidence"),
                            reasoning=parsed.get("reasoning", ""),
                            sources=parsed.get("sources", []),
                            raw_output=raw_output,
                            input_tokens=usage.get("input_tokens", 0),
                            output_tokens=usage.get("output_tokens", 0),
                            truth_claims=parsed.get("truth_claims", []),
                        )
            except json.JSONDecodeError:
                continue

        # Strategy 2: Find any line with probability/confidence in text content
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                # Check assistant message with text content
                if isinstance(data, dict) and data.get("type") == "assistant":
                    message = data.get("message", {})
                    content_list = message.get("content", [])
                    for item in content_list:
                        if isinstance(item, dict) and item.get("type") == "text":
                            text = item.get("text", "")
                            parsed = self._parse_json_from_text(text)
                            if parsed and ("probability" in parsed or "confidence" in parsed):
                                usage = message.get("usage", {})
                                return Result(
                                    probability=parsed.get("probability"),
                                    confidence=parsed.get("confidence"),
                                    reasoning=parsed.get("reasoning", ""),
                                    sources=parsed.get("sources", []),
                                    raw_output=raw_output,
                                    input_tokens=usage.get("input_tokens", 0),
                                    output_tokens=usage.get("output_tokens", 0),
                                    truth_claims=parsed.get("truth_claims", []),
                                )
            except json.JSONDecodeError:
                continue

        # Fallback: plain JSON in output
        return super()._extract_result(raw_output, returncode)

    def _parse_json_from_text(self, text: str) -> dict | None:
        """Extract JSON from text that may contain markdown code blocks."""
        if not text:
            return None

        # Try parsing the whole text as JSON
        text = text.strip()
        if text.startswith("{") and text.endswith("}"):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass

        # Try extracting from markdown code blocks: ```json ... ``` or ``` ... ```
        code_block_pattern = r"```(?:json)?\s*\n?(.*?)\n?\s*```"
        matches = re.findall(code_block_pattern, text, re.DOTALL)
        for match in matches:
            match = match.strip()
            if match.startswith("{") and match.endswith("}"):
                try:
                    return json.loads(match)
                except json.JSONDecodeError:
                    continue

        # Try finding JSON object in text (greedy)
        json_pattern = r"\{[^{}]*\"probability\"[^{}]*\}"
        matches = re.findall(json_pattern, text, re.DOTALL)
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue

        return None
