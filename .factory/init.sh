#!/bin/bash
set -e

cd /home/lukashonke/projects/listening-companion/claude-code

# Backend dependencies
cd backend && uv sync && cd ..

# Frontend dependencies
cd frontend && npm install && cd ..

# Ensure images directory exists for local dev
mkdir -p backend/images

echo "Init complete."
