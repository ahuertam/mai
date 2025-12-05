#!/usr/bin/env bash
set -euo pipefail

MODEL=${MODEL:-llama3.1:8b}
OLLAMA_HOST=${OLLAMA_HOST:-http://localhost:11434}

if command -v py >/dev/null 2>&1; then
  py -3 -m venv .venv
elif command -v python3 >/dev/null 2>&1; then
  python3 -m venv .venv
elif command -v python >/dev/null 2>&1; then
  python -m venv .venv
else
  echo "Python no encontrado. Instala Python 3.10+" >&2
  exit 1
fi

if [ -f ".venv/Scripts/python.exe" ]; then
  VENV_PY=".venv/Scripts/python.exe"
else
  VENV_PY=".venv/bin/python"
fi

"$VENV_PY" -m pip install --upgrade pip
"$VENV_PY" -m pip install ollama

if command -v ollama >/dev/null 2>&1; then
  if command -v curl >/dev/null 2>&1; then
    if ! curl --max-time 5 -s "${OLLAMA_HOST%/}/api/tags" >/dev/null; then
      echo "Iniciando servicio de Ollama..."
      if nohup ollama serve >/dev/null 2>&1 & then sleep 2; fi
      for i in $(seq 1 10); do
        if curl --max-time 5 -s "${OLLAMA_HOST%/}/api/tags" >/dev/null; then break; fi
        sleep 1
      done
    fi
    if curl --max-time 5 -s "${OLLAMA_HOST%/}/api/tags" >/dev/null; then
      echo "Ollama activo en localhost:11434"
      ollama pull "$MODEL" || true
    else
      echo "Ollama no activo. Inícialo manualmente."
    fi
  else
    echo "Instala curl para comprobar Ollama o verifica manualmente."
    ollama pull "$MODEL" || true
  fi
else
  uname_s="$(uname -s)"
  if [ "$uname_s" = "Linux" ]; then
    if command -v curl >/dev/null 2>&1; then
      echo "Instalando Ollama en Linux..."
      curl -fsSL https://ollama.com/install.sh | sh || echo "Instalación fallida."
    else
      echo "Instala curl para poder instalar Ollama (Linux)."
    fi
  elif [ "$uname_s" = "Darwin" ]; then
    echo "Instala Ollama con Homebrew: brew install ollama"
  else
    echo "CLI de Ollama no encontrado. En Windows usa https://ollama.com/download"
  fi
fi

printf "MAI_MODEL=%s\n" "$MODEL" > .env
printf "OLLAMA_HOST=%s\n" "$OLLAMA_HOST" >> .env
echo "Configuración escrita en .env: MAI_MODEL=$MODEL, OLLAMA_HOST=$OLLAMA_HOST"

echo "Entorno listo. Ejecuta: \"$VENV_PY\" main.py"