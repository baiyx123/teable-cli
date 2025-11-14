#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teable CLI - 命令行界面工具包
"""

__version__ = "0.1.0"
__author__ = "Teable CLI Team"
__description__ = "A command-line interface for Teable database"

from .cli import main
from .config import Config
from .session import Session

__all__ = ["main", "Config", "Session"]
