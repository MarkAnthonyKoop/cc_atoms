"""Prompt loading with composition and search path support"""
from pathlib import Path
from typing import Optional, List

from cc_atoms.config import PROMPT_SEARCH_PATHS


class PromptLoader:
    """
    Load prompts with composition and search paths.

    Searches for prompts in priority order:
    1. Project-local (.atom/prompts/)
    2. Global (~/cc_atoms/prompts/)
    3. User override (ATOM_PROMPTS_PATH env var)
    """

    def load(self, toolname: Optional[str] = None) -> str:
        """
        Load system prompt(s) based on toolname.

        Rules:
        - toolname=None -> ATOM.md
        - toolname='atom_foo' -> ATOM.md + FOO.md
        - toolname='foo' -> FOO.md only

        Args:
            toolname: Optional tool name for specialized prompts

        Returns:
            Combined prompt text

        Raises:
            FileNotFoundError: If required prompt file not found

        Examples:
            >>> loader = PromptLoader()
            >>> loader.load()  # Returns ATOM.md
            >>> loader.load("atom_test")  # Returns ATOM.md + TEST.md
            >>> loader.load("test")  # Returns TEST.md only
        """
        # Determine which files to load
        if toolname is None:
            files = ["ATOM.md"]
        elif toolname.startswith("atom_"):
            files = ["ATOM.md", f"{toolname[5:].upper()}.md"]
        else:
            files = [f"{toolname.upper()}.md"]

        # Load and combine
        contents = []
        for filename in files:
            filepath = self._find_prompt(filename)
            if not filepath:
                raise FileNotFoundError(
                    f"Prompt {filename} not found in search paths: {PROMPT_SEARCH_PATHS}"
                )
            contents.append(filepath.read_text())

        return "\n\n".join(contents)

    def _find_prompt(self, filename: str) -> Optional[Path]:
        """
        Find prompt file in search paths.

        Args:
            filename: Prompt filename to find

        Returns:
            Path to file, or None if not found
        """
        for search_path in PROMPT_SEARCH_PATHS:
            if not search_path.exists():
                continue
            filepath = search_path / filename
            if filepath.exists():
                return filepath
        return None

    def get_available_prompts(self) -> List[str]:
        """
        Get list of all available prompts across search paths.

        Returns:
            List of prompt names (without .md extension)
        """
        prompts = set()

        for search_path in PROMPT_SEARCH_PATHS:
            if not search_path.exists():
                continue

            for prompt_file in search_path.glob("*.md"):
                prompts.add(prompt_file.stem.lower())

        return sorted(prompts)
