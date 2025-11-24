#!/usr/bin/env python3
import sys
import os

# Calculate absolute paths
project_root = os.path.dirname(os.path.abspath(__file__))
venv_python = os.path.join(project_root, ".venv", "Scripts", "python.exe")
cli_script = os.path.join(project_root, "src", "cli.py")

# Build command
cmd = [venv_python, cli_script] + sys.argv[1:]

# Execute
os.execv(venv_python, cmd)