#!/usr/bin/env bash
set -euo pipefail

if [ -f .env ]; then set -a; . ./.env; set +a; fi

MODEL=${MAI_MODEL:-llama3.1:8b}
HOST=${OLLAMA_HOST:-http://localhost:11434}

if command -v py >/dev/null 2>&1; then
  py -3 -m venv .venv || true
elif command -v python3 >/dev/null 2>&1; then
  python3 -m venv .venv || true
elif command -v python >/dev/null 2>&1; then
  python -m venv .venv || true
fi

if [ -f ".venv/Scripts/python.exe" ]; then
  VENV_PY=".venv/Scripts/python.exe"
else
  VENV_PY=".venv/bin/python"
fi

"$VENV_PY" -m pip install --upgrade pip
"$VENV_PY" -m pip install ollama

if ! command -v ollama >/dev/null 2>&1; then
  uname_s="$(uname -s)"
  if [ "$uname_s" = "Linux" ] && command -v curl >/dev/null 2>&1; then
    curl -fsSL https://ollama.com/install.sh | sh || true
  fi
fi

if command -v ollama >/dev/null 2>&1; then
  if command -v curl >/dev/null 2>&1; then
    if ! curl --max-time 5 -s "${HOST%/}/api/tags" >/dev/null 2>&1; then
      nohup ollama serve >/dev/null 2>&1 &
      sleep 2
      for i in $(seq 1 10); do
        if curl --max-time 5 -s "${HOST%/}/api/tags" >/dev/null 2>&1; then break; fi
        sleep 1
      done
    fi
  fi
  ollama pull "$MODEL" || true
fi

"$VENV_PY" main.py