#!/bin/bash
set -e
echo "Installing dependencies..."
pip install -r requirements.txt -q
if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env - edit it and add your ANTHROPIC_API_KEY"
fi
mkdir -p uploads
echo ""
echo "Setup complete!"
echo "Edit .env to add your ANTHROPIC_API_KEY, then run: python run.py"
