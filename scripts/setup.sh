#!/usr/bin/env bash
# ─────────────────────────────────────────────
# Agam Automation Hub — First-Time Setup Script
# Usage: bash scripts/setup.sh
# ─────────────────────────────────────────────
set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${CYAN}▶ Agam Automation Hub — Setup${NC}"
echo "──────────────────────────────────────────"

# Python check
if ! command -v python3 &>/dev/null; then
  echo "❌ python3 not found. Install Python 3.10+ first."; exit 1
fi
PYVER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "  Python: ${GREEN}${PYVER}${NC}"

# Node check
if ! command -v node &>/dev/null; then
  echo -e "${YELLOW}⚠  node not found — frontend won't work (backend-only mode still works)${NC}"
else
  echo -e "  Node:   ${GREEN}$(node --version)${NC}"
fi

# Virtual environment
if [ ! -d "venv" ]; then
  echo -e "${CYAN}▶ Creating virtual environment...${NC}"
  python3 -m venv venv
fi

echo -e "${CYAN}▶ Installing Python dependencies...${NC}"
venv/bin/pip install --upgrade pip -q
venv/bin/pip install -r requirements.txt -q
echo -e "  ${GREEN}✓ Python deps installed${NC}"

# Frontend
if command -v node &>/dev/null && [ -f "frontend/package.json" ]; then
  echo -e "${CYAN}▶ Installing frontend dependencies...${NC}"
  cd frontend && npm install --silent && cd ..
  echo -e "  ${GREEN}✓ Frontend deps installed${NC}"
fi

# .env setup
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo -e "  ${YELLOW}⚠  .env created from template — add your ANTHROPIC_API_KEY!${NC}"
else
  echo -e "  .env already exists — skipping"
fi

# Output directories
mkdir -p output/jobs output/linkedin/queue output/briefings data
echo -e "  ${GREEN}✓ Output directories created${NC}"

echo ""
echo -e "${GREEN}✅ Setup complete!${NC}"
echo ""
echo "  Next steps:"
echo "  1. Edit .env → add ANTHROPIC_API_KEY (required)"
echo "  2. Run: make web   (or: python run_web.py --mode both)"
echo "  3. Open: http://localhost:8000 (backend) | http://localhost:5173 (frontend)"
echo ""
