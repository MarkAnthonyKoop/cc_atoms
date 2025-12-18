"""Prompt parsing utilities for atom_gui."""
import json
import re
import sys
from pathlib import Path


class PromptParser:
    """Parse session logs to extract individual prompts and responses."""

    @staticmethod
    def parse_session_log(content):
        """Extract prompts and responses from session log markdown."""
        prompts = []

        # Pattern to match user prompts and assistant responses
        sections = re.split(r'^## (👤 User|🤖 Assistant)', content, flags=re.MULTILINE)

        current_type = None
        current_content = []

        for i, section in enumerate(sections):
            if section in ['👤 User', '🤖 Assistant']:
                # Save previous section
                if current_type and current_content:
                    text = ''.join(current_content).strip()
                    if text:
                        prompts.append({
                            'type': current_type,
                            'content': text,
                            'preview': text[:80].replace('\n', ' ')
                        })

                # Start new section
                current_type = 'user' if 'User' in section else 'assistant'
                current_content = []
            else:
                current_content.append(section)

        # Save last section
        if current_type and current_content:
            text = ''.join(current_content).strip()
            if text:
                prompts.append({
                    'type': current_type,
                    'content': text,
                    'preview': text[:80].replace('\n', ' ')
                })

        return prompts

    @staticmethod
    def parse_jsonl_file(jsonl_path):
        """Extract prompts directly from JSONL file."""
        prompts = []

        try:
            lines = Path(jsonl_path).read_text().splitlines()

            for line in lines:
                if not line.strip():
                    continue

                try:
                    data = json.loads(line)

                    # Check if this is a user or assistant message
                    if data.get("type") in ["user", "assistant"]:
                        role = data.get("message", {}).get("role")

                        if role in ["user", "assistant"]:
                            content_raw = data.get("message", {}).get("content", "")

                            # Content can be string or list of blocks
                            content = ""
                            if isinstance(content_raw, str):
                                content = content_raw
                            elif isinstance(content_raw, list):
                                # Extract text from content blocks
                                for block in content_raw:
                                    if isinstance(block, dict) and block.get("type") == "text":
                                        content += block.get("text", "")
                                    elif isinstance(block, str):
                                        content += block

                            if content:
                                prompts.append({
                                    'type': role,
                                    'content': content,
                                    'preview': content[:80].replace('\n', ' ')
                                })

                except json.JSONDecodeError:
                    continue

        except Exception as e:
            print(f"Error parsing JSONL: {e}", file=sys.stderr)

        return prompts
