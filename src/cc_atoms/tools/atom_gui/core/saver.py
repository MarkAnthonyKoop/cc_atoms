"""Session file saving utilities for atom_gui."""
import json
import sys
from pathlib import Path


class SessionSaver:
    """Handles saving edits back to JSONL session files."""

    @staticmethod
    def find_jsonl_file(session_dir):
        """Find the JSONL session file for a given session directory."""
        # Claude Code stores sessions in ~/.claude/projects/
        claude_projects = Path.home() / ".claude" / "projects"

        if not claude_projects.exists():
            return None

        # Convert session path to Claude's format: -path-to-dir
        try:
            session_path_str = str(session_dir.resolve())
            # Remove leading slash, replace / and _ with -
            mangled_path = session_path_str.replace("/", "-").replace("_", "-")

            project_dir = claude_projects / mangled_path

            if not project_dir.exists():
                return None

            # Find the most recent JSONL file (can be session-*.jsonl or UUID.jsonl)
            jsonl_files = sorted(project_dir.glob("*.jsonl"),
                               key=lambda p: p.stat().st_mtime,
                               reverse=True)

            if jsonl_files:
                return jsonl_files[0]

        except Exception as e:
            print(f"Error finding JSONL file: {e}", file=sys.stderr)

        return None

    @staticmethod
    def get_original_content(session_dir, prompt_index, prompt_type):
        """Get the original content of a prompt before editing."""
        jsonl_file = SessionSaver.find_jsonl_file(session_dir)

        if not jsonl_file:
            return None

        try:
            lines = jsonl_file.read_text().splitlines()
            message_count = 0

            for line in lines:
                if not line.strip():
                    continue

                try:
                    data = json.loads(line)

                    if data.get("type") in ["user", "assistant"]:
                        role = data.get("message", {}).get("role")

                        if role in ["user", "assistant"]:
                            target_type = "user" if prompt_type == "user" else "assistant"

                            if role == target_type:
                                if message_count == prompt_index:
                                    # Found the message
                                    if "message" in data and "content" in data["message"]:
                                        return data["message"]["content"]

                                message_count += 1

                except json.JSONDecodeError:
                    continue

        except Exception as e:
            print(f"Error getting original content: {e}", file=sys.stderr)

        return None

    @staticmethod
    def save_prompt_edit(session_dir, prompt_index, new_content, prompt_type):
        """Save edited prompt back to JSONL file."""
        jsonl_file = SessionSaver.find_jsonl_file(session_dir)

        if not jsonl_file:
            return False, "Could not find JSONL session file"

        try:
            # Read all lines
            lines = jsonl_file.read_text().splitlines()

            # Track user/assistant messages
            message_count = 0
            modified = False

            for i, line in enumerate(lines):
                if not line.strip():
                    continue

                try:
                    data = json.loads(line)

                    # Check if this is a user or assistant message
                    if data.get("type") in ["user", "assistant"]:
                        role = data.get("message", {}).get("role")

                        if role in ["user", "assistant"]:
                            # Check if this is the message we want to edit
                            target_type = "user" if prompt_type == "user" else "assistant"

                            if role == target_type:
                                if message_count == prompt_index:
                                    # Found the message to edit
                                    if "message" in data and "content" in data["message"]:
                                        # Update the content (string format)
                                        data["message"]["content"] = new_content
                                        modified = True

                                        # Update the line
                                        lines[i] = json.dumps(data)
                                        break

                                message_count += 1

                except json.JSONDecodeError:
                    continue

            if not modified:
                return False, f"Could not find message at index {prompt_index}"

            # Write back to file
            jsonl_file.write_text('\n'.join(lines) + '\n')

            return True, "Successfully saved to JSONL file"

        except Exception as e:
            return False, f"Error saving: {str(e)}"

    @staticmethod
    def apply_undo_redo(jsonl_path, prompt_index, content, prompt_type):
        """Apply an undo or redo action directly to JSONL file."""
        jsonl_file = Path(jsonl_path)

        if not jsonl_file.exists():
            return False, f"JSONL file not found: {jsonl_file}"

        try:
            lines = jsonl_file.read_text().splitlines()
            message_count = 0
            modified = False

            for i, line in enumerate(lines):
                if not line.strip():
                    continue

                try:
                    data = json.loads(line)

                    if data.get("type") in ["user", "assistant"]:
                        role = data.get("message", {}).get("role")

                        if role in ["user", "assistant"]:
                            target_type = "user" if prompt_type == "user" else "assistant"

                            if role == target_type:
                                if message_count == prompt_index:
                                    # Found the message
                                    if "message" in data and "content" in data["message"]:
                                        data["message"]["content"] = content
                                        modified = True
                                        lines[i] = json.dumps(data)
                                        break

                                message_count += 1

                except json.JSONDecodeError:
                    continue

            if not modified:
                return False, f"Could not find message at index {prompt_index}"

            # Write back to file
            jsonl_file.write_text('\n'.join(lines) + '\n')

            return True, "Successfully applied undo/redo"

        except Exception as e:
            return False, f"Error applying undo/redo: {str(e)}"
