"""Tests for the tools module."""

import asyncio
import os
import pytest
import tempfile
from pathlib import Path

from cc.tools import (
    BashTool,
    ReadTool,
    WriteTool,
    EditTool,
    GlobTool,
    GrepTool,
    ToolExecutor,
    PermissionChecker,
    ToolRegistry,
)


class TestBashTool:
    """Tests for BashTool."""

    @pytest.mark.asyncio
    async def test_execute_simple_command(self):
        """Test executing a simple command."""
        bash = BashTool()
        result = await bash.execute(command="echo hello")
        assert result.success
        assert "hello" in result.output

    @pytest.mark.asyncio
    async def test_execute_command_with_error(self):
        """Test executing a command that fails."""
        bash = BashTool()
        result = await bash.execute(command="exit 1")
        assert not result.success
        assert result.metadata.get("exit_code") == 1

    @pytest.mark.asyncio
    async def test_execute_no_command(self):
        """Test executing with no command."""
        bash = BashTool()
        result = await bash.execute()
        assert not result.success
        assert "No command" in result.error

    @pytest.mark.asyncio
    async def test_execute_with_cwd(self):
        """Test executing with custom working directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bash = BashTool(cwd=tmpdir)
            result = await bash.execute(command="pwd")
            assert result.success
            assert tmpdir in result.output

    def test_get_definition(self):
        """Test getting tool definition."""
        definition = BashTool.get_definition()
        assert definition["name"] == "Bash"
        assert "command" in definition["input_schema"]["properties"]


class TestReadTool:
    """Tests for ReadTool."""

    @pytest.mark.asyncio
    async def test_read_file(self):
        """Test reading a file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("line1\nline2\nline3\n")
            temp_path = f.name

        try:
            read = ReadTool()
            result = await read.execute(file_path=temp_path)
            assert result.success
            assert "line1" in result.output
            assert "line2" in result.output
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_read_file_with_offset(self):
        """Test reading with offset."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("line1\nline2\nline3\nline4\nline5\n")
            temp_path = f.name

        try:
            read = ReadTool()
            result = await read.execute(file_path=temp_path, offset=2, limit=2)
            assert result.success
            assert "line3" in result.output
            assert "line4" in result.output
            assert "line1" not in result.output
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self):
        """Test reading a file that doesn't exist."""
        read = ReadTool()
        result = await read.execute(file_path="/nonexistent/path/file.txt")
        assert not result.success
        assert "does not exist" in result.error

    @pytest.mark.asyncio
    async def test_read_directory(self):
        """Test reading a directory (should fail)."""
        read = ReadTool()
        result = await read.execute(file_path=tempfile.gettempdir())
        assert not result.success
        assert "Cannot read directory" in result.error


class TestWriteTool:
    """Tests for WriteTool."""

    @pytest.mark.asyncio
    async def test_write_new_file(self):
        """Test writing a new file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "test.txt")
            write = WriteTool()
            result = await write.execute(file_path=file_path, content="hello world")
            assert result.success
            assert "Created" in result.output
            assert os.path.exists(file_path)
            with open(file_path) as f:
                assert f.read() == "hello world"

    @pytest.mark.asyncio
    async def test_write_existing_file(self):
        """Test overwriting an existing file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("old content")
            temp_path = f.name

        try:
            write = WriteTool()
            result = await write.execute(file_path=temp_path, content="new content")
            assert result.success
            assert "Updated" in result.output
            with open(temp_path) as f:
                assert f.read() == "new content"
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_write_creates_directories(self):
        """Test that write creates parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "a", "b", "c", "test.txt")
            write = WriteTool()
            result = await write.execute(file_path=file_path, content="nested")
            assert result.success
            assert os.path.exists(file_path)


class TestEditTool:
    """Tests for EditTool."""

    @pytest.mark.asyncio
    async def test_edit_replace(self):
        """Test editing a file with replacement."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("hello world")
            temp_path = f.name

        try:
            edit = EditTool()
            result = await edit.execute(
                file_path=temp_path,
                old_string="hello",
                new_string="goodbye"
            )
            assert result.success
            with open(temp_path) as f:
                assert f.read() == "goodbye world"
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_edit_replace_all(self):
        """Test replacing all occurrences."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("hello hello hello")
            temp_path = f.name

        try:
            edit = EditTool()
            result = await edit.execute(
                file_path=temp_path,
                old_string="hello",
                new_string="hi",
                replace_all=True
            )
            assert result.success
            with open(temp_path) as f:
                assert f.read() == "hi hi hi"
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_edit_not_unique(self):
        """Test editing fails when string is not unique."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("hello hello")
            temp_path = f.name

        try:
            edit = EditTool()
            result = await edit.execute(
                file_path=temp_path,
                old_string="hello",
                new_string="hi"
            )
            assert not result.success
            assert "appears 2 times" in result.error
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_edit_string_not_found(self):
        """Test editing fails when string is not found."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("hello world")
            temp_path = f.name

        try:
            edit = EditTool()
            result = await edit.execute(
                file_path=temp_path,
                old_string="xyz",
                new_string="abc"
            )
            assert not result.success
            assert "not found" in result.error
        finally:
            os.unlink(temp_path)


class TestGlobTool:
    """Tests for GlobTool."""

    @pytest.mark.asyncio
    async def test_glob_pattern(self):
        """Test globbing with a pattern."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            Path(tmpdir, "test1.txt").touch()
            Path(tmpdir, "test2.txt").touch()
            Path(tmpdir, "test.py").touch()

            glob = GlobTool(cwd=tmpdir)
            result = await glob.execute(pattern="*.txt")
            assert result.success
            assert "test1.txt" in result.output
            assert "test2.txt" in result.output
            assert "test.py" not in result.output

    @pytest.mark.asyncio
    async def test_glob_recursive(self):
        """Test recursive globbing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create nested structure
            subdir = Path(tmpdir, "subdir")
            subdir.mkdir()
            Path(tmpdir, "root.py").touch()
            Path(subdir, "nested.py").touch()

            glob = GlobTool(cwd=tmpdir)
            result = await glob.execute(pattern="**/*.py")
            assert result.success
            assert "root.py" in result.output
            assert "nested.py" in result.output

    @pytest.mark.asyncio
    async def test_glob_no_matches(self):
        """Test globbing with no matches."""
        with tempfile.TemporaryDirectory() as tmpdir:
            glob = GlobTool(cwd=tmpdir)
            result = await glob.execute(pattern="*.xyz")
            assert result.success
            assert "No files matching" in result.output


class TestGrepTool:
    """Tests for GrepTool."""

    @pytest.mark.asyncio
    async def test_grep_simple(self):
        """Test simple grep."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir, "test.txt")
            file_path.write_text("hello world\nfoo bar\nhello again\n")

            grep = GrepTool(cwd=tmpdir)
            result = await grep.execute(
                pattern="hello",
                path=str(file_path),
                output_mode="content"
            )
            assert result.success
            assert "hello world" in result.output
            assert "hello again" in result.output

    @pytest.mark.asyncio
    async def test_grep_files_only(self):
        """Test grep returning only file names."""
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "match.txt").write_text("hello world")
            Path(tmpdir, "nomatch.txt").write_text("foo bar")

            grep = GrepTool(cwd=tmpdir)
            result = await grep.execute(
                pattern="hello",
                path=tmpdir,
                output_mode="files_with_matches"
            )
            assert result.success
            assert "match.txt" in result.output
            assert "nomatch.txt" not in result.output

    @pytest.mark.asyncio
    async def test_grep_case_insensitive(self):
        """Test case insensitive grep."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir, "test.txt")
            file_path.write_text("Hello World\n")

            grep = GrepTool(cwd=tmpdir)
            result = await grep.execute(
                pattern="hello",
                path=str(file_path),
                output_mode="content",
                **{"-i": True}
            )
            assert result.success
            assert "Hello World" in result.output


class TestPermissionChecker:
    """Tests for PermissionChecker."""

    def test_skip_permissions(self):
        """Test skipping permissions."""
        checker = PermissionChecker(skip_permissions=True)
        assert checker.is_allowed("Bash", {"command": "rm -rf /"})

    def test_allow_pattern(self):
        """Test allow pattern matching."""
        checker = PermissionChecker(allow_patterns=["Bash(git:*)"])
        assert checker.is_allowed("Bash", {"command": "git status"})
        assert not checker.is_allowed("Bash", {"command": "rm file"})

    def test_deny_pattern(self):
        """Test deny pattern matching."""
        checker = PermissionChecker(deny_patterns=["Bash(rm:*)"])
        assert checker.is_allowed("Bash", {"command": "git status"})
        assert not checker.is_allowed("Bash", {"command": "rm file"})

    def test_deny_takes_precedence(self):
        """Test deny patterns take precedence over allow."""
        checker = PermissionChecker(
            allow_patterns=["Bash*"],
            deny_patterns=["Bash(rm:*)"]
        )
        assert checker.is_allowed("Bash", {"command": "git status"})
        assert not checker.is_allowed("Bash", {"command": "rm file"})


class TestToolRegistry:
    """Tests for ToolRegistry."""

    def test_registry_has_builtin_tools(self):
        """Test registry has all builtin tools."""
        registry = ToolRegistry()
        tools = registry.list_tools()
        assert "Bash" in tools
        assert "Read" in tools
        assert "Write" in tools
        assert "Edit" in tools
        assert "Glob" in tools
        assert "Grep" in tools

    def test_get_tool(self):
        """Test getting a tool by name."""
        registry = ToolRegistry()
        bash = registry.get_tool("Bash")
        assert bash is not None
        assert bash.name == "Bash"

    def test_get_definitions(self):
        """Test getting all tool definitions."""
        registry = ToolRegistry()
        definitions = registry.get_definitions()
        assert len(definitions) == 6
        names = [d["name"] for d in definitions]
        assert "Bash" in names


class TestToolExecutor:
    """Tests for ToolExecutor."""

    @pytest.mark.asyncio
    async def test_execute_bash(self):
        """Test executing bash through executor."""
        executor = ToolExecutor()
        result = await executor.execute("Bash", {"command": "echo test"})
        assert result.success
        assert "test" in result.output

    @pytest.mark.asyncio
    async def test_execute_unknown_tool(self):
        """Test executing unknown tool."""
        executor = ToolExecutor()
        result = await executor.execute("UnknownTool", {})
        assert not result.success
        assert "Unknown tool" in result.error

    @pytest.mark.asyncio
    async def test_execute_with_permission_denied(self):
        """Test executing with permission denied."""
        permission_checker = PermissionChecker(deny_patterns=["Bash*"])
        executor = ToolExecutor(permission_checker=permission_checker)
        result = await executor.execute("Bash", {"command": "echo test"})
        assert not result.success
        assert "Permission denied" in result.error

    def test_get_tool_definitions(self):
        """Test getting tool definitions from executor."""
        executor = ToolExecutor()
        definitions = executor.get_tool_definitions()
        assert len(definitions) == 6
