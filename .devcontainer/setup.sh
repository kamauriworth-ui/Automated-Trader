#!/usr/bin/env bash
# One-time setup for the cloud development environment (GitHub Codespaces).
set -e

echo "Installing Python libraries..."
pip install --quiet -r requirements.txt

# Create .env from the template, but never overwrite one you've already edited.
if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi

echo ""
echo "Setup complete. Try:"
echo "  python -m trader         # run the app"
echo "  python -m pytest -v      # run the tests"
