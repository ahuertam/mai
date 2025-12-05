$ErrorActionPreference = "Stop"
param(
  [string]$Model = "llama3.1:8b",
  [string]$OllamaHost = "http://localhost:11434"
)

function Resolve-Python {
  $py = Get-Command py -ErrorAction SilentlyContinue
  if ($py) { return "py -3" }
  $python = Get-Command python -ErrorAction SilentlyContinue
  if ($python) { return $python.Path }
  throw "Python no encontrado. Instala Python 3.10+"
}

$pycmd = Resolve-Python

if ($pycmd -eq "py -3") {
  & py -3 -m venv .venv
} else {
  & $pycmd -m venv .venv
}

$venvPython = Join-Path ".\.venv\Scripts" "python.exe"

& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install ollama

$ollamaCli = Get-Command ollama -ErrorAction SilentlyContinue

if (-not $ollamaCli) {
  $winget = Get-Command winget -ErrorAction SilentlyContinue
  if ($winget) {
    Write-Host "Instalando Ollama con winget..."
    try {
      winget install --silent --accept-source-agreements --accept-package-agreements Ollama.Ollama | Out-Null
    } catch {
      Write-Host "No se pudo instalar Ollama vía winget."
    }
    $ollamaCli = Get-Command ollama -ErrorAction SilentlyContinue
  }
}

if ($ollamaCli) {
  $running = $false
  try {
    Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -TimeoutSec 3 | Out-Null
    $running = $true
  } catch {}

  if (-not $running) {
    Write-Host "Iniciando servicio de Ollama..."
    try {
      Start-Process -FilePath $ollamaCli.Path -ArgumentList "serve" -WindowStyle Hidden | Out-Null
      Start-Sleep -Seconds 2
    } catch {
      Write-Host "No se pudo iniciar Ollama automáticamente."
    }
    $tries = 0
    while ($tries -lt 10 -and -not $running) {
      try {
        Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -TimeoutSec 3 | Out-Null
        $running = $true
        break
      } catch { Start-Sleep -Seconds 1; $tries++ }
    }
  }

  if ($running) {
    Write-Host "Ollama activo en localhost:11434"
    try { & $ollamaCli.Path pull $Model } catch {}
  } else {
    Write-Host "Ollama no activo. Ábrelo manualmente desde el menú Inicio o app."
  }
} else {
  Write-Host "CLI de Ollama no encontrado. Instala desde https://ollama.com/download (Windows 10+)"
}

try {
  $envPath = Join-Path (Get-Location) ".env"
  "MAI_MODEL=$Model" | Out-File -FilePath $envPath -Encoding UTF8
  "OLLAMA_HOST=$OllamaHost" | Out-File -FilePath $envPath -Encoding UTF8 -Append
  Write-Host "Configuración escrita en .env: MAI_MODEL=$Model, OLLAMA_HOST=$OllamaHost"
} catch {
  Write-Host "No se pudo escribir el archivo .env"
}

Write-Host "Entorno listo. Ejecuta: .\.venv\Scripts\python.exe main.py"