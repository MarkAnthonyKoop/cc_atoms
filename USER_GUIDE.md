# CC_Atoms User Guide

**Complete guide to autonomous Claude Code orchestration**

---

## Table of Contents

- [Quickstart (5 Minutes)](#quickstart-5-minutes)
- [Core Concepts](#core-concepts)
- [Installation & Setup](#installation--setup)
- [Basic Usage](#basic-usage)
- [Tool Ecosystem](#tool-ecosystem)
- [Advanced Workflows](#advanced-workflows)
- [Detailed Use Cases](#detailed-use-cases)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)
- [Tips & Tricks](#tips--tricks)
- [Reference](#reference)

---

## Quickstart (5 Minutes)

### What is cc_atoms?

CC_Atoms is an autonomous orchestration system for Claude Code that enables AI-powered iterative problem-solving. It breaks complex tasks into manageable pieces, maintains context across iterations, and can create specialized tools for reusable capabilities.

**Think of it as:** A recursive AI system that manages its own workflow, creating sub-tasks when needed and building tools to solve problems systematically.

### Install in 3 Steps

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd cc

# 2. Run atom.py once to initialize
python3 atom.py --help

# 3. Add to your PATH (optional but recommended)
echo 'export PATH="$HOME/cc_atoms/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### Your First Atom Session

```bash
# Create a directory for your task
mkdir my-first-atom
cd my-first-atom

# Run atom with a simple task
atom "Create a Python script that prints the first 10 Fibonacci numbers"

# Watch as atom:
# - Reads your prompt
# - Creates the Python script
# - Tests it
# - Documents it in README.md
# - Signals completion with EXIT_LOOP_NOW
```

**That's it!** You've run your first autonomous session. Check `README.md` to see what happened.

---

## Core Concepts

### 1. What is an Atom?

An **atom** is an autonomous Claude Code session that:
- Has a specific task in `USER_PROMPT.md`
- Iterates up to 25 times to complete the task
- Maintains context automatically via `claude -c`
- Documents its work in `README.md`
- Can spawn sub-atoms for complex subtasks
- Signals completion with `EXIT_LOOP_NOW`

### 2. Session Structure

Every atom session has this structure:

```
my-task/
├── USER_PROMPT.md      # Your task specification (required)
├── README.md           # Living documentation (maintained by atom)
├── session_log.md      # Full conversation history (optional)
└── <your files>        # Whatever the atom creates
```

### 3. Iteration Loop

```
Iteration 1: Read USER_PROMPT.md → Plan → Execute → Update README.md
Iteration 2: Read context + README.md → Continue → Update README.md
Iteration 3: Read context + README.md → Finish → Output EXIT_LOOP_NOW
```

Each iteration builds on previous work. Context accumulates automatically.

### 4. Decomposition

When a task is too complex, atom creates **sub-atoms**:

```
main-task/
├── USER_PROMPT.md
├── README.md
└── subtask-1/              # Sub-atom!
    ├── USER_PROMPT.md
    ├── README.md
    └── <files>
```

Sub-atoms run independently, then results integrate back to parent.

### 5. Tool Creation

For reusable capabilities, atom creates **tools**:

```bash
atom_create_tool "Create a code review tool"
# → Creates atom_code_reviewer in ~/cc_atoms/tools/
```

Tools become part of your workflow, callable from any session.

---

## Installation & Setup

### Prerequisites

- **Python 3.7+** (for atom scripts)
- **Claude Code CLI** (`claude` command available)
- **Git** (for version control)
- **Optional**: `pipx install claude-conversation-extractor` (for session logs)

### Detailed Installation

#### 1. Clone Repository

```bash
git clone <your-repo-url> ~/cc_atoms_project
cd ~/cc_atoms_project
```

#### 2. Initialize Environment

```bash
# Run atom.py to create ~/cc_atoms structure
python3 atom.py --help

# This creates:
# ~/cc_atoms/
# ├── bin/           # Tool launchers
# ├── tools/         # Tool implementations
# ├── prompts/       # System prompts
# └── tests/         # Test suite
```

#### 3. Add to PATH

**For Bash:**
```bash
echo 'export PATH="$HOME/cc_atoms/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

**For Zsh:**
```bash
echo 'export PATH="$HOME/cc_atoms/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

**For Fish:**
```fish
set -U fish_user_paths $HOME/cc_atoms/bin $fish_user_paths
```

#### 4. Verify Installation

```bash
# Should show help
atom --help

# Should list available tools
ls ~/cc_atoms/bin/
```

### Directory Structure Reference

```
~/cc_atoms/                    # Installed tools and infrastructure
├── bin/                       # Executable launchers (in PATH)
│   ├── atom -> /path/to/atom.py
│   ├── atom_gui
│   ├── atom_create_tool
│   └── atom_session_analyzer
├── tools/                     # Tool implementations
│   ├── atom_gui/
│   ├── atom_create_tool/
│   └── atom_session_analyzer/
├── prompts/                   # System prompts
│   ├── ATOM.md               # Base atom prompt
│   ├── CREATE_TOOL.md        # Tool creation prompt
│   └── SESSION_ANALYZER.md   # Session analysis prompt
└── tests/                     # Test suite
    └── test_atom.py

~/my-projects/                 # Your work directories
├── project-1/                # Each project gets its own atom session
│   ├── USER_PROMPT.md
│   ├── README.md
│   └── <files>
└── project-2/
    ├── USER_PROMPT.md
    ├── README.md
    └── <files>
```

---

## Basic Usage

### Method 1: Command-Line Prompt

The simplest way - just tell atom what to do:

```bash
# Atom creates USER_PROMPT.md for you
atom "Create a TODO app with SQLite backend"
```

**What happens:**
1. Atom writes your prompt to `USER_PROMPT.md`
2. Starts iterating immediately
3. Creates all necessary files
4. Documents in `README.md`
5. Exits when complete

### Method 2: USER_PROMPT.md File

For more complex tasks, write a detailed prompt:

```bash
mkdir complex-task
cd complex-task

# Create detailed prompt
cat > USER_PROMPT.md << 'EOF'
Create a Python web scraper that:
1. Scrapes product prices from example.com
2. Stores data in SQLite
3. Sends email alerts when prices drop
4. Includes error handling and logging
5. Has comprehensive tests

Requirements:
- Use requests + BeautifulSoup
- Async with asyncio
- Type hints throughout
- 80%+ test coverage
EOF

# Run atom
atom
```

### Method 3: Specialized Tools

Use specialized prompts for specific tasks:

```bash
# With tool-specific behavior
atom --toolname atom_test "Write comprehensive tests for auth.py"

# Just the tool behavior (no base atom capabilities)
atom --toolname test "Run the test suite and fix failures"
```

### Understanding Output

During execution, you'll see:

```
🔬 Atom: my-task

============================================================
Iteration 1/25
============================================================

<Claude's work appears here>

============================================================
Iteration 2/25
============================================================

<More work>

✅ Complete after 3 iterations
```

### Checking Results

```bash
# View documentation
cat README.md

# See full conversation
cat session_log.md  # If extracted

# Check created files
ls -la
```

---

## Tool Ecosystem

### Built-in Tools

#### 1. `atom` - Core Orchestrator

**Purpose:** Run autonomous sessions

```bash
# Basic usage
atom "Your task here"

# With USER_PROMPT.md
atom

# With specialized tool
atom --toolname atom_test "Test the authentication module"
```

**Options:**
- `--toolname <name>`: Use specialized system prompt
- Accepts prompt as arguments or reads `USER_PROMPT.md`

#### 2. `atom_gui` - Session Monitor

**Purpose:** Real-time GUI for monitoring atom sessions

```bash
# Monitor current directory
atom_gui

# Monitor specific directory
atom_gui /path/to/project

# Features:
# - Tree view of all sessions
# - README.md viewer
# - Session log viewer
# - Edit prompts in JSONL files
# - Undo/redo support
# - Auto-refresh every 2 seconds
```

**Key Features:**
- **Sessions Tree**: Hierarchical view of all atom sessions
- **Prompt List**: Individual user/assistant prompts
- **Edit Prompts**: Modify prompts directly in JSONL
- **Save & Undo**: Full history with undo/redo
- **Real-time**: Auto-refreshes as atom works

**Keyboard Shortcuts:**
- `F5`: Refresh sessions
- Standard copy/paste in editor

#### 3. `atom_create_tool` - Tool Generator

**Purpose:** Create new specialized tools

```bash
# Interactive mode
atom_create_tool
# Prompts for: name, description, features

# AI-assisted mode
atom_create_tool "Create a code review tool that checks Python files"
```

**Generates:**
- Python script at `~/cc_atoms/tools/<name>/`
- System prompt at `~/cc_atoms/prompts/<NAME>.md`
- Launcher at `~/cc_atoms/bin/<name>`
- README documentation

**Example:**
```bash
atom_create_tool "Create atom_deployer that deploys to AWS"
# Creates:
# ~/cc_atoms/tools/atom_deployer/atom_deployer.py
# ~/cc_atoms/prompts/DEPLOYER.md
# ~/cc_atoms/bin/atom_deployer
# ~/cc_atoms/tools/atom_deployer/README.md
```

#### 4. `atom_session_analyzer` - Session Extractor

**Purpose:** Extract and analyze Claude Code sessions

```bash
# Extract current session
atom_session_analyzer
# Creates: session_log.md

# Extract and analyze
atom_session_analyzer "Summarize key decisions made"
# Creates session_log.md + runs analysis
```

**Requires:** `pipx install claude-conversation-extractor`

**Output Format:**
```markdown
# Claude Code Session

## 👤 User
Your prompt here...

## 🤖 Assistant
Response here...

## 👤 User
Next prompt...
```

---

## Advanced Workflows

### Workflow 1: Complex Multi-Step Project

**Scenario:** Build a complete web application

```bash
# 1. Create project directory
mkdir web-app
cd web-app

# 2. Create detailed USER_PROMPT.md
cat > USER_PROMPT.md << 'EOF'
Build a Flask web application with:

Backend:
- User authentication (JWT)
- RESTful API for CRUD operations
- PostgreSQL database
- Redis caching

Frontend:
- React SPA
- Responsive design
- Form validation

DevOps:
- Docker compose setup
- CI/CD with GitHub Actions
- Environment configuration

Testing:
- Unit tests (pytest)
- Integration tests
- E2E tests (Playwright)

Documentation:
- API docs (Swagger)
- Deployment guide
- User manual
EOF

# 3. Run atom
atom

# 4. Monitor progress in separate terminal
atom_gui .
```

**What happens:**
1. Atom reads the complex prompt
2. Decides to decompose into sub-atoms:
   - `backend/` - API and database
   - `frontend/` - React app
   - `devops/` - Docker and CI/CD
   - `tests/` - Test suite
3. Each sub-atom completes independently
4. Results integrate back to main README.md

### Workflow 2: Iterative Refinement

**Scenario:** Start simple, add features iteratively

```bash
mkdir calculator
cd calculator

# Iteration 1: Basic calculator
atom "Create a Python CLI calculator with +, -, *, /"

# Check result
python calculator.py

# Iteration 2: Add features
atom "Add support for: parentheses, exponents, scientific notation"

# Iteration 3: More features
atom "Add: command history, variables, function definitions"

# Each iteration builds on previous work!
```

### Workflow 3: Research & Implementation

**Scenario:** Research then implement

```bash
mkdir ml-model
cd ml-model

# Step 1: Research
atom "Research best practices for training sentiment analysis models"
# Creates: research_findings.md

# Step 2: Design
atom "Based on research, design architecture for sentiment analysis API"
# Creates: architecture.md, design_decisions.md

# Step 3: Implement
atom "Implement the sentiment analysis model and API as designed"
# Creates: actual implementation

# Step 4: Test & Document
atom "Add comprehensive tests and deployment documentation"
```

### Workflow 4: Tool Creation & Use

**Scenario:** Create reusable tool, then use it

```bash
# Step 1: Create tool
atom_create_tool "Create atom_benchmark that profiles Python code performance"

# Step 2: Use the tool
cd ~/my-project
atom --toolname atom_benchmark "Profile the database query functions"

# The tool has specialized knowledge about profiling!
```

### Workflow 5: Session Analysis

**Scenario:** Learn from previous sessions

```bash
cd completed-project

# Extract session
atom_session_analyzer

# Analyze decisions
atom_session_analyzer "Extract all architectural decisions and their rationale"

# Creates detailed analysis of why choices were made
```

---

## Detailed Use Cases

### Use Case 1: Building a CLI Tool

**Goal:** Create a feature-rich command-line tool

**Setup:**
```bash
mkdir cli-tool
cd cli-tool
```

**USER_PROMPT.md:**
```markdown
Create a Python CLI tool called 'taskmaster' for task management:

Features:
- Add, list, complete, delete tasks
- Priority levels (high, medium, low)
- Due dates with reminders
- Tags for categorization
- Search and filter
- SQLite storage
- Colored output with rich
- Export to JSON/CSV

Requirements:
- Use Click for CLI framework
- Type hints throughout
- Comprehensive error handling
- 90%+ test coverage
- User documentation
- Example usage in README

Output:
- Installable package with setup.py
- Working executable
- Full test suite
```

**Run:**
```bash
atom
```

**Expected Result:**
```
cli-tool/
├── USER_PROMPT.md
├── README.md
├── setup.py
├── taskmaster/
│   ├── __init__.py
│   ├── cli.py
│   ├── models.py
│   ├── database.py
│   └── utils.py
├── tests/
│   ├── test_cli.py
│   ├── test_models.py
│   └── test_database.py
└── docs/
    └── usage.md
```

**Install & Use:**
```bash
pip install -e .
taskmaster add "Finish documentation" --priority high --due tomorrow
taskmaster list
taskmaster complete 1
```

### Use Case 2: API Integration

**Goal:** Integrate with external API

**Setup:**
```bash
mkdir weather-app
cd weather-app
```

**USER_PROMPT.md:**
```markdown
Create a weather dashboard that:

1. Fetches data from OpenWeatherMap API
2. Displays current weather + 5-day forecast
3. Supports multiple cities
4. Caches API responses (1 hour TTL)
5. Has CLI and web interface

Technical:
- Async API calls with aiohttp
- FastAPI for web server
- React frontend (optional)
- Environment variables for API key
- Error handling for rate limits
- Retry logic with exponential backoff

Deliverables:
- Working application
- Configuration template (.env.example)
- Docker setup
- API documentation
```

**Run & Monitor:**
```bash
# Terminal 1
atom

# Terminal 2
atom_gui .
```

**Result:**
```
weather-app/
├── USER_PROMPT.md
├── README.md
├── .env.example
├── docker-compose.yml
├── backend/
│   ├── main.py
│   ├── api_client.py
│   ├── cache.py
│   └── models.py
├── frontend/
│   └── <React app>
└── tests/
    └── <test files>
```

### Use Case 3: Data Processing Pipeline

**Goal:** Build ETL pipeline

**Setup:**
```bash
mkdir data-pipeline
cd data-pipeline
```

**USER_PROMPT.md:**
```markdown
Create a data processing pipeline:

Source: CSV files from S3
Transform: Clean, normalize, enrich
Destination: PostgreSQL database

Components:
1. S3 downloader with retry logic
2. CSV parser with validation
3. Data cleaner (handle nulls, duplicates)
4. Data enricher (geocoding, categorization)
5. Database loader with upserts
6. Error handling and logging
7. Monitoring dashboard

Requirements:
- Process 1M+ rows efficiently
- Parallel processing with multiprocessing
- Checkpoint/resume capability
- Data quality reports
- Airflow DAG (optional)

Tests:
- Unit tests for each component
- Integration test with test data
- Performance benchmarks
```

**Run:**
```bash
atom
```

**Decomposition:** Atom will likely create:
```
data-pipeline/
├── USER_PROMPT.md
├── README.md
├── downloader/         # Sub-atom for S3 download
├── transformer/        # Sub-atom for ETL logic
├── loader/            # Sub-atom for DB loading
├── monitoring/        # Sub-atom for dashboard
└── integration/       # Main integration
```

### Use Case 4: Testing Existing Code

**Goal:** Add comprehensive tests to existing project

**Setup:**
```bash
cd existing-project

# Create atom session for testing
mkdir testing-session
cd testing-session
```

**USER_PROMPT.md:**
```markdown
Add comprehensive tests to the parent directory project:

Current state:
- Django web application
- No tests currently
- Located in ../

Requirements:
1. Analyze the codebase
2. Create test plan
3. Implement tests:
   - Unit tests for models
   - Unit tests for views
   - Integration tests for API
   - End-to-end tests for key workflows
4. Achieve 80%+ coverage
5. Setup CI to run tests
6. Document testing strategy

Constraints:
- Don't modify existing code (unless bugs found)
- Use pytest + pytest-django
- Mock external services
- Fast test execution (<2 min)
```

**Run:**
```bash
atom
```

**Expected Work:**
1. Analyze existing code
2. Create `../tests/` directory
3. Write comprehensive test suite
4. Create `pytest.ini`, `conftest.py`
5. Setup GitHub Actions
6. Generate coverage report

### Use Case 5: Documentation Generation

**Goal:** Create comprehensive documentation

**Setup:**
```bash
cd my-library
mkdir docs-generation
cd docs-generation
```

**USER_PROMPT.md:**
```markdown
Generate comprehensive documentation for the Python library in ../

Include:
1. API Reference (auto-generated from docstrings)
2. User Guide with examples
3. Tutorial for beginners
4. Advanced usage patterns
5. FAQ
6. Contributing guide
7. Architecture overview

Technical:
- Use Sphinx
- Auto-generate API docs from code
- Include code examples that actually run
- Create docs/ directory in parent
- Setup ReadTheDocs configuration
- Searchable documentation

Output:
- docs/ directory with source
- Built HTML documentation
- GitHub Pages deployment ready
```

**Run:**
```bash
atom
```

### Use Case 6: Code Refactoring

**Goal:** Refactor messy code

**Setup:**
```bash
cd legacy-project
mkdir refactoring-session
cd refactoring-session
```

**USER_PROMPT.md:**
```markdown
Refactor the codebase in ../ for better maintainability:

Current issues:
- 2000-line god objects
- No separation of concerns
- Duplicate code
- No type hints
- Poor naming

Refactoring goals:
1. Break up large files into focused modules
2. Extract common functionality
3. Add type hints
4. Improve naming
5. Add docstrings
6. Ensure tests still pass

Approach:
- Incremental refactoring
- Run tests after each change
- Document refactoring decisions
- Create migration guide

Deliverables:
- Refactored code
- Before/after comparison
- Refactoring report
- Breaking changes documented
```

**Run:**
```bash
atom
```

Atom will refactor systematically while maintaining functionality.

### Use Case 7: Custom Tool Creation

**Goal:** Create a specialized analysis tool

**Scenario:**
```bash
atom_create_tool
```

**Interactive Prompts:**
```
Tool name: atom_security_scanner
Description: Scan Python code for security vulnerabilities
Key features:
  - Detect SQL injection risks
  - Check for hardcoded secrets
  - Analyze dependency vulnerabilities
  - Generate security report
```

**What Gets Created:**
```
~/cc_atoms/tools/atom_security_scanner/
├── atom_security_scanner.py
├── README.md
└── scanner_logic.py

~/cc_atoms/prompts/
└── SECURITY_SCANNER.md

~/cc_atoms/bin/
└── atom_security_scanner
```

**Use the Tool:**
```bash
cd my-project
atom --toolname atom_security_scanner "Scan this project for security issues"
```

The tool now has specialized knowledge about security scanning!

### Use Case 8: Multi-Project Workflow

**Goal:** Work on related projects simultaneously

**Setup:**
```bash
mkdir microservices
cd microservices
```

**Structure:**
```
microservices/
├── USER_PROMPT.md          # Main orchestrator
├── README.md
├── auth-service/           # Sub-atom
│   ├── USER_PROMPT.md
│   └── README.md
├── api-gateway/           # Sub-atom
│   ├── USER_PROMPT.md
│   └── README.md
└── data-service/          # Sub-atom
    ├── USER_PROMPT.md
    └── README.md
```

**Main USER_PROMPT.md:**
```markdown
Build a microservices architecture:

Services:
1. Auth Service (JWT authentication)
2. API Gateway (routing, rate limiting)
3. Data Service (CRUD operations)

Each service should:
- Have its own repository structure
- Include Dockerfile
- Have comprehensive tests
- Include API documentation

Integration:
- Docker Compose for local dev
- Shared types/interfaces
- Service discovery
- Health checks

Note: Decompose into sub-atoms for each service
```

**Run:**
```bash
atom
```

Atom creates sub-atoms for each service, then integrates them.

### Use Case 9: Learning & Exploration

**Goal:** Learn a new technology

**Setup:**
```bash
mkdir learn-rust
cd learn-rust
```

**USER_PROMPT.md:**
```markdown
Help me learn Rust through practical examples:

1. Start with "Hello World"
2. Explain ownership and borrowing with examples
3. Create small projects demonstrating concepts:
   - CLI calculator
   - File reader/writer
   - HTTP server
   - Async programming
4. Include detailed comments explaining each concept
5. Provide exercises with solutions
6. Create a learning roadmap

Deliverables:
- Progressive examples (beginner → advanced)
- Detailed explanations
- Practice exercises
- Resources for further learning
```

**Run:**
```bash
atom
```

Atom creates a structured learning path with runnable examples.

### Use Case 10: CI/CD Pipeline Setup

**Goal:** Add CI/CD to existing project

**Setup:**
```bash
cd my-project
mkdir cicd-setup
cd cicd-setup
```

**USER_PROMPT.md:**
```markdown
Setup complete CI/CD pipeline for the project in ../

Requirements:
1. GitHub Actions workflows
2. Pipeline stages:
   - Lint (black, ruff, mypy)
   - Test (pytest with coverage)
   - Build (Docker image)
   - Deploy (staging → production)
3. Environment management
4. Secret management
5. Rollback capability

Deliverables:
- .github/workflows/ directory
- Deployment scripts
- Environment configuration
- Documentation for running/debugging
```

**Run:**
```bash
atom
```

---

## Best Practices

### 1. Writing Good Prompts

**❌ Too Vague:**
```
Create a website
```

**✅ Specific & Detailed:**
```
Create a portfolio website with:
- 3 pages: Home, Projects, Contact
- Responsive design using Tailwind CSS
- Project cards with images and descriptions
- Contact form with validation
- Deployed to Netlify
```

**Tips:**
- Be specific about requirements
- Include technical constraints
- Specify deliverables
- Mention testing needs
- Add examples if helpful

### 2. Organizing Sessions

**Use Descriptive Directory Names:**
```bash
# ❌ Bad
mkdir test
mkdir proj

# ✅ Good
mkdir user-authentication-system
mkdir data-migration-tool
```

**Group Related Work:**
```
my-app/
├── phase-1-backend/
├── phase-2-frontend/
├── phase-3-tests/
└── phase-4-deployment/
```

### 3. When to Decompose

**Decompose when task has:**
- 3+ distinct components
- Multiple technologies
- Parallel workstreams
- Research + implementation

**Example:**
```
main-task/
├── USER_PROMPT.md → "Build full-stack app"
├── research/       → "Research tech stack options"
├── backend/        → "Build API"
├── frontend/       → "Build UI"
└── devops/        → "Setup deployment"
```

### 4. Monitoring Progress

**During Long Sessions:**
```bash
# Terminal 1: Run atom
cd project
atom

# Terminal 2: Monitor
atom_gui /path/to/project

# Terminal 3: Watch README
watch -n 2 cat project/README.md
```

### 5. Iterative Development

**Build in Stages:**
```bash
# Stage 1: MVP
atom "Create basic TODO app with add/list"

# Test it
python todo.py

# Stage 2: Features
atom "Add: edit, delete, search, filters"

# Stage 3: Polish
atom "Add: colors, help text, error messages"
```

### 6. Handling Errors

**If Atom Gets Stuck:**
1. Check `README.md` for current state
2. Review session with `atom_session_analyzer`
3. Create new prompt based on current state
4. Consider decomposing if too complex

**If Tests Fail:**
```bash
# Let atom fix them!
atom "The tests in test_auth.py are failing. Debug and fix them."
```

### 7. Documentation Practices

**Good README.md Structure:**
```markdown
# Project Name

## Overview
Brief description

## Status
COMPLETE / IN_PROGRESS / BLOCKED

## Progress
- [x] Task 1
- [x] Task 2
- [ ] Task 3

## Current State
What exists now

## Next Steps
What's remaining

## Decisions
Why choices were made
```

### 8. Tool Development

**When to Create Tools:**
- Repetitive tasks (testing, deployment)
- Specialized analysis (security, performance)
- Domain-specific workflows (ML pipelines)

**Tool Naming:**
- `atom_*` for tools that build on atom capabilities
- Other names for standalone tools

### 9. Version Control

**Commit Strategy:**
```bash
# After each successful iteration
git add .
git commit -m "Iteration 3: Added authentication"

# After completion
git commit -m "Complete: User authentication system"
```

### 10. Reusing Atoms

**Save Successful Prompts:**
```bash
# Create template
mkdir ~/atom-templates
cp successful-project/USER_PROMPT.md ~/atom-templates/web-api-template.md

# Use template
cat ~/atom-templates/web-api-template.md > USER_PROMPT.md
# Edit as needed
atom
```

---

## Troubleshooting

### Problem: Atom Doesn't Exit

**Symptoms:**
- Reaches MAX_ITERATIONS (25)
- Never outputs EXIT_LOOP_NOW

**Solutions:**

1. **Check README.md:**
   ```bash
   cat README.md
   # Is atom stuck on something? Blocked?
   ```

2. **Review Status:**
   ```markdown
   ## Status
   BLOCKED - Waiting for API key
   ```
   Provide what's needed in a new prompt.

3. **Simplify the Task:**
   ```bash
   # New prompt with clearer end condition
   atom "Complete just the authentication module. Output EXIT_LOOP_NOW when it's working with tests passing."
   ```

### Problem: Sub-atoms Not Created

**Symptoms:**
- Atom tries to do everything in one session
- Gets overwhelmed

**Solutions:**

1. **Explicitly Request Decomposition:**
   ```markdown
   This task is complex. Please:
   1. Analyze the components
   2. Create sub-atoms for each major component
   3. Integrate results in main README
   ```

2. **Pre-create Structure:**
   ```bash
   mkdir backend frontend tests
   # Atom will recognize these as potential sub-atoms
   ```

### Problem: "ATOM.md not found"

**Symptoms:**
```
❌ /Users/you/cc_atoms/prompts/ATOM.md not found
```

**Solutions:**

1. **Ensure ~/cc_atoms exists:**
   ```bash
   ls ~/cc_atoms/prompts/ATOM.md
   ```

2. **Copy from source:**
   ```bash
   cp /path/to/cc/prompts/ATOM.md ~/cc_atoms/prompts/
   ```

3. **Reinitialize:**
   ```bash
   cd /path/to/cc
   python3 atom.py --help
   ```

### Problem: Session Limit Reached

**Symptoms:**
```
⏳ Session limit - waiting until reset (60 minutes)
```

**Solutions:**

1. **Wait:** Atom will automatically retry after reset
2. **Use Different Directory:** Work on another task
3. **Manual Resume:** Continue later with same context

### Problem: atom_gui Not Showing Sessions

**Symptoms:**
- GUI shows no sessions
- Tree is empty

**Solutions:**

1. **Check for README.md:**
   ```bash
   # Sessions need README.md with "## Status"
   find . -name "README.md" -exec grep -l "## Status" {} \;
   ```

2. **Refresh:**
   - Press F5 in GUI
   - Or click "Refresh" button

3. **Run in Correct Directory:**
   ```bash
   atom_gui /path/to/projects/root
   ```

### Problem: Can't Edit Prompts in GUI

**Symptoms:**
- "Could not find JSONL session file"

**Solutions:**

1. **Ensure Active Session:**
   ```bash
   # Session must be in ~/.claude/projects/
   claude -c -p "test"  # Creates session
   ```

2. **Extract Session Log:**
   - Click "Extract Log" in GUI
   - Requires `claude-conversation-extractor`

3. **Install Extractor:**
   ```bash
   pipx install claude-conversation-extractor
   ```

### Problem: Import Errors

**Symptoms:**
```python
ModuleNotFoundError: No module named 'config'
```

**Solutions:**

1. **Run from Correct Location:**
   ```bash
   # Run atom.py from its directory
   cd /path/to/cc
   python3 atom.py
   ```

2. **Check Python Path:**
   ```bash
   echo $PYTHONPATH
   # Should include /path/to/cc
   ```

3. **Use Absolute Paths:**
   ```bash
   /full/path/to/atom.py "task"
   ```

---

## Tips & Tricks

### Tip 1: Chain Atoms

```bash
# Research → Design → Implement
atom "Research best practices for rate limiting APIs" && \
atom "Design rate limiting architecture based on research" && \
atom "Implement the rate limiting system"
```

### Tip 2: Parallel Development

```bash
# Work on frontend and backend simultaneously
cd frontend && atom "Build React UI" &
cd backend && atom "Build FastAPI backend" &
wait
```

### Tip 3: Template Prompts

**Create reusable templates:**

```bash
# Save template
cat > ~/.atom-templates/python-cli.md << 'EOF'
Create a Python CLI tool with:
- Click framework
- Subcommands
- --help documentation
- Type hints
- Tests with pytest
- Setup.py for installation

Tool name: {{NAME}}
Purpose: {{PURPOSE}}
Commands: {{COMMANDS}}
EOF

# Use template
sed -e 's/{{NAME}}/mytool/g' \
    -e 's/{{PURPOSE}}/Task management/g' \
    -e 's/{{COMMANDS}}/add, list, done/g' \
    ~/.atom-templates/python-cli.md > USER_PROMPT.md

atom
```

### Tip 4: Quick Experiments

```bash
# Use /tmp for throwaway experiments
cd /tmp
mkdir experiment-$$  # Unique dir
cd experiment-$$
atom "Test if pandas can read this CSV format: <paste data>"
```

### Tip 5: Session Comparison

```bash
# Compare two approaches
mkdir approach-a approach-b

cd approach-a
atom "Implement using asyncio"

cd ../approach-b
atom "Implement using threading"

# Compare README.md files
diff approach-a/README.md approach-b/README.md
```

### Tip 6: Progress Tracking

```bash
# Track multiple projects
atom_gui ~/projects &  # Monitor all projects

# Or use watch
watch -n 5 'find ~/projects -name README.md -exec grep -H "^## Status" {} \;'
```

### Tip 7: Debugging with Session Logs

```bash
# Extract detailed session
atom_session_analyzer

# Search for specific decisions
grep -A 5 "decided to" session_log.md

# Find all tool uses
grep -B 2 -A 2 "Tool:" session_log.md
```

### Tip 8: Custom Workflows

**Create workflow scripts:**

```bash
#!/bin/bash
# new-api-project.sh

PROJECT=$1
mkdir -p "$PROJECT"/{api,tests,docs}

cat > "$PROJECT/USER_PROMPT.md" << EOF
Create a REST API with:
- FastAPI framework
- PostgreSQL database
- JWT authentication
- Comprehensive tests
- OpenAPI documentation

Endpoints: <describe endpoints>
EOF

cd "$PROJECT"
atom
```

Usage:
```bash
./new-api-project.sh my-awesome-api
```

### Tip 9: Integration with Other Tools

**Git Hooks:**
```bash
# .git/hooks/pre-commit
#!/bin/bash
if [ -f "README.md" ]; then
  # Ensure README is up to date
  git add README.md
fi
```

**VS Code Integration:**
```json
// .vscode/tasks.json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Run Atom",
      "type": "shell",
      "command": "atom",
      "args": ["${input:atomPrompt}"],
      "presentation": {
        "reveal": "always",
        "panel": "new"
      }
    }
  ],
  "inputs": [
    {
      "id": "atomPrompt",
      "type": "promptString",
      "description": "What should atom do?"
    }
  ]
}
```

### Tip 10: Atom as Documentation

```bash
# Use atoms to explain your code
mkdir explain-auth
cd explain-auth

cat > USER_PROMPT.md << 'EOF'
Analyze the authentication system in ../src/auth/ and create:
1. Architecture diagram (Mermaid)
2. Flow charts for login/logout
3. Explanation of security measures
4. How to add new auth providers
EOF

atom
```

---

## Reference

### Command Reference

#### atom

```bash
# Synopsis
atom [OPTIONS] [PROMPT...]

# Options
--toolname TOOL    Use specialized tool prompt

# Examples
atom "Create a CLI calculator"
atom --toolname atom_test "Test the API endpoints"
atom  # Uses existing USER_PROMPT.md
```

#### atom_gui

```bash
# Synopsis
atom_gui [DIRECTORY]

# Examples
atom_gui              # Monitor current directory
atom_gui ~/projects   # Monitor specific directory

# Features
- F5: Refresh
- Auto-refresh: 2 seconds
- Edit prompts in JSONL
- Undo/redo support
```

#### atom_create_tool

```bash
# Synopsis
atom_create_tool [DESCRIPTION]

# Examples
atom_create_tool                              # Interactive mode
atom_create_tool "Create a deployment tool"   # AI-assisted

# Creates
~/cc_atoms/tools/<toolname>/
~/cc_atoms/prompts/<TOOLNAME>.md
~/cc_atoms/bin/<toolname>
```

#### atom_session_analyzer

```bash
# Synopsis
atom_session_analyzer [PROMPT]

# Examples
atom_session_analyzer                    # Extract only
atom_session_analyzer "Summarize key decisions"  # Extract + analyze

# Requires
pipx install claude-conversation-extractor

# Output
session_log.md in current directory
```

### File Format Reference

#### USER_PROMPT.md

```markdown
# Free-form task description

Can include:
- Requirements
- Constraints
- Examples
- Links to resources
- Acceptance criteria
```

#### README.md (Generated)

```markdown
# Project Title

## Overview
Brief description

## Status
COMPLETE | IN_PROGRESS | BLOCKED | NEEDS_DECOMPOSITION

## Progress
- [x] Completed task
- [ ] Pending task

## Current State
What exists now

## Next Steps
What's remaining

## Decisions
- Why we chose X over Y
- Rationale for approach
```

### Environment Variables

```bash
# Optional configuration
export ATOM_MAX_ITERATIONS=50      # Default: 25
export ATOM_EXIT_SIGNAL="DONE"     # Default: EXIT_LOOP_NOW
export ATOM_HOME=~/my_atoms        # Default: ~/cc_atoms
```

### Exit Codes

- `0`: Success (task completed)
- `1`: Error (prompt file missing, etc.)
- `130`: Interrupted (Ctrl+C)

### Configuration Files

#### config.py

```python
# Paths
ATOMS_HOME = Path.home() / "cc_atoms"
BIN_DIR = ATOMS_HOME / "bin"
TOOLS_DIR = ATOMS_HOME / "tools"
PROMPTS_DIR = ATOMS_HOME / "prompts"

# Iteration settings
MAX_ITERATIONS = 25
EXIT_SIGNAL = "EXIT_LOOP_NOW"

# Retry settings
NETWORK_RETRY_BASE = 5
NETWORK_RETRY_MAX = 300
```

#### .editorconfig

```ini
[*.py]
indent_style = space
indent_size = 4
max_line_length = 100
```

#### pyproject.toml

```toml
[tool.black]
line-length = 100

[tool.ruff]
line-length = 100
```

---

## FAQ

### General Questions

**Q: How is this different from just using Claude Code?**

A: Atoms add:
- Automatic iteration and context management
- Structured documentation in README.md
- Ability to decompose complex tasks
- Reusable tool creation
- Progress tracking across sessions

**Q: Can atoms write any kind of code?**

A: Yes! Atoms can work with any programming language, framework, or technology that Claude Code supports.

**Q: How many iterations does it take to complete a task?**

A: Typically 3-10 iterations for most tasks. Complex tasks may decompose into sub-atoms.

**Q: Can I stop and resume an atom?**

A: Yes. Ctrl+C to stop. Run `atom` again to resume with full context.

### Technical Questions

**Q: Where is session data stored?**

A:
- Work files: Current directory
- Session history: `~/.claude/projects/`
- Tools: `~/cc_atoms/`

**Q: Can I modify the system prompts?**

A: Yes! Edit files in `~/cc_atoms/prompts/`. Changes affect future sessions.

**Q: How does context accumulation work?**

A: Claude Code's `-c` flag automatically includes previous outputs in each iteration.

**Q: Can atoms access the internet?**

A: Yes, through Claude Code's capabilities. Can fetch docs, APIs, etc.

### Workflow Questions

**Q: Should I create a new directory for each task?**

A: Recommended. Keeps sessions isolated and organized.

**Q: Can I run multiple atoms simultaneously?**

A: Yes! Each directory is independent. Monitor with `atom_gui`.

**Q: How do I share atom work with others?**

A: Share the directory (including README.md). They can continue with `atom`.

**Q: Can atoms commit to git?**

A: Yes! Atoms can create commits, branches, and even PRs.

---

## Getting Help

### Documentation

- **This Guide**: Comprehensive usage
- **README.md**: Project overview and quick start
- **ARCHITECTURE.md**: System design and internals
- **Tool READMEs**: Specific tool documentation

### Community

- GitHub Issues: Report bugs
- Discussions: Ask questions
- Examples: See example sessions

### Debugging

```bash
# Check installation
atom --help
ls ~/cc_atoms/

# Verify Claude Code
claude --version

# Test with simple task
atom "Print hello world in Python"

# Check session logs
atom_session_analyzer
```

---

## Appendix

### A. Keyboard Shortcuts

#### atom_gui

- `F5`: Refresh sessions
- `Ctrl+C` / `Cmd+C`: Copy text
- `Ctrl+V` / `Cmd+V`: Paste text
- `Ctrl+X` / `Cmd+X`: Cut text
- `Ctrl+Z` / `Cmd+Z`: Undo (in editor)

### B. Status Values

- `COMPLETE`: Task finished successfully
- `IN_PROGRESS`: Currently working
- `BLOCKED`: Waiting for something
- `NEEDS_DECOMPOSITION`: Too complex, should split
- `UNKNOWN`: Status unclear

### C. Common Patterns

**Pattern: Progressive Enhancement**
```
1. MVP iteration
2. Add features
3. Add tests
4. Add documentation
5. Performance optimization
```

**Pattern: Research → Design → Build**
```
1. Research best practices
2. Design architecture
3. Implement core
4. Add features
5. Polish and test
```

**Pattern: Test-Driven**
```
1. Write tests first
2. Implement to pass tests
3. Refactor for quality
4. Document behavior
```

### D. Example Prompts Library

**Simple CLI Tool:**
```markdown
Create a command-line tool in [LANGUAGE] that:
- [PRIMARY FUNCTION]
- Has [COMMANDS]
- Includes help text
- Has basic error handling
```

**Web API:**
```markdown
Create a REST API with [FRAMEWORK]:
- Endpoints: [LIST]
- Database: [TYPE]
- Authentication: [METHOD]
- Tests with [TOOL]
- API documentation
```

**Data Processing:**
```markdown
Create a data pipeline that:
- Reads from [SOURCE]
- Transforms: [OPERATIONS]
- Writes to [DESTINATION]
- Handles errors gracefully
- Provides progress feedback
```

**Testing:**
```markdown
Add comprehensive tests to [PROJECT]:
- Unit tests for [COMPONENTS]
- Integration tests for [FLOWS]
- Achieve [COVERAGE]% coverage
- Use [FRAMEWORK]
```

---

**End of User Guide**

For the latest updates and examples, visit the project repository.

Happy atomizing! 🔬
