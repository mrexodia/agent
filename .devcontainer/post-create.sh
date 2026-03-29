#!/bin/bash

# Exit on error
set -e

# Shell prompt - only add if not already present
grep -qF "PS1='\$(if [[ \"\$PWD\" == /workspaces/* ]];" ~/.bashrc || echo "PS1='\$(if [[ \"\$PWD\" == /workspaces/* ]]; then realpath --relative-to=/workspaces \"\$PWD\"; else echo \"\\w\"; fi)\\$ '" >> ~/.bashrc

# Build project
uv sync
cmake -B build -G Ninja --fresh
cmake --build build
