"""Setup script for CC CLI."""

from setuptools import setup, find_packages
from pathlib import Path

# Read version without importing the package
__version__ = "0.1.0"

# Read README for long description
readme_path = Path(__file__).parent / "README.md"
long_description = ""
if readme_path.exists():
    long_description = readme_path.read_text(encoding="utf-8")

setup(
    name="cc-cli",
    version=__version__,
    description="CC CLI - A Claude Code CLI clone for interactive AI conversations",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="CC CLI Project",
    python_requires=">=3.9",
    packages=find_packages(exclude=["tests", "tests.*"]),
    install_requires=[
        "anthropic>=0.40.0",
        "rich>=13.0.0",
        "prompt_toolkit>=3.0.0",
        "watchdog>=3.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "cc=cc.main:main",
            "cc-analytics=cc.tools.cc_analytics:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
