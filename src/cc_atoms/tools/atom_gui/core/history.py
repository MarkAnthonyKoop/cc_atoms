"""Edit history management for atom_gui."""
import time


class EditHistory:
    """Manages undo/redo history for JSONL edits."""

    def __init__(self):
        self.history = []  # List of edit actions
        self.current_position = -1  # Position in history (-1 = no history)

    def add_edit(self, jsonl_path, prompt_index, prompt_type, old_content, new_content):
        """Add an edit to history."""
        # Remove any "future" history if we're not at the end
        if self.current_position < len(self.history) - 1:
            self.history = self.history[:self.current_position + 1]

        # Add new edit
        self.history.append({
            'jsonl_path': str(jsonl_path),
            'prompt_index': prompt_index,
            'prompt_type': prompt_type,
            'old_content': old_content,
            'new_content': new_content,
            'timestamp': time.time()
        })

        self.current_position = len(self.history) - 1

    def can_undo(self):
        """Check if undo is available."""
        return self.current_position >= 0

    def can_redo(self):
        """Check if redo is available."""
        return self.current_position < len(self.history) - 1

    def get_undo_action(self):
        """Get the action to undo (returns None if can't undo)."""
        if not self.can_undo():
            return None

        action = self.history[self.current_position]
        return {
            'jsonl_path': action['jsonl_path'],
            'prompt_index': action['prompt_index'],
            'prompt_type': action['prompt_type'],
            'content': action['old_content']  # Restore old content
        }

    def get_redo_action(self):
        """Get the action to redo (returns None if can't redo)."""
        if not self.can_redo():
            return None

        action = self.history[self.current_position + 1]
        return {
            'jsonl_path': action['jsonl_path'],
            'prompt_index': action['prompt_index'],
            'prompt_type': action['prompt_type'],
            'content': action['new_content']  # Restore new content
        }

    def move_back(self):
        """Move back in history (after undo)."""
        if self.can_undo():
            self.current_position -= 1

    def move_forward(self):
        """Move forward in history (after redo)."""
        if self.can_redo():
            self.current_position += 1

    def get_history_info(self):
        """Get info about current history state."""
        return {
            'total': len(self.history),
            'position': self.current_position + 1,
            'can_undo': self.can_undo(),
            'can_redo': self.can_redo()
        }
