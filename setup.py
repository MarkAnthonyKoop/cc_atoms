#!/usr/bin/env python3
"""Backwards compatibility setup.py for editable installs.

All configuration is in pyproject.toml. This file only exists for
older pip versions that require setup.py for editable installs.
"""
from setuptools import setup

setup()
