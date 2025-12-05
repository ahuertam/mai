$ErrorActionPreference = "Stop"
param(
  [string]$Model = "llama3.1:8b",
  [string]$OllamaHost = "http://localhost:11434"
)

function Load-Env {
  $envPath = Join-Path (Get-Location) ".env"
  if (Test-Path $envPath) {
    Get-Content $envPath | ForEach-Object {
      $line = $_.Trim()
      if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
        $parts = $line.Split("=",2)
        $k = $parts[0].Trim()
        $v = $parts[1].Trim()
        $env:$k = $v
      }
    }
  }
}

Load-Env
if ($env:MAI_MODEL) { $Model = $env:MAI_MODEL }
if ($env:OLLAMA_HOST) { $OllamaHost = $env:OLLAMA_HOST }

function Resolve-Python {
  $py = Get-Command py -ErrorAction SilentlyContinue
  if ($py) { return "py -3" }
  $python = Get-Command python -ErrorAction SilentlyContinue
  if ($python) { return $python.Path }
  throw "Python no encontrado. Instala Python 3.10+"
}

$pycmd = Resolve-Python
if ($pycmd -eq "py -3") { & py -3 -m venv .venv } else { & $pycmd -m venv .venv }

$venvPython = Join-Path ".\.venv\Scripts" "python.exe"
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install ollama

$ollamaCli = Get-Command ollama -ErrorAction SilentlyContinue
if (-not $ollamaCli) {
  $winget = Get-Command winget -ErrorAction SilentlyContinue
  if ($winget) {
    try { winget install --silent --accept-source-agreements --accept-package-agreements Ollama.Ollama | Out-Null } catch {}
    $ollamaCli = Get-Command ollama -ErrorAction SilentlyContinue
  }
}

if ($ollamaCli) {
  $running = $false
  try {
    Invoke-WebRequest -Uri ($OllamaHost.TrimEnd('/') + "/api/tags") -UseBasicParsing -TimeoutSec 3 | Out-Null
    $running = $true
  } catch {}
  if (-not $running) {
    try { Start-Process -FilePath $ollamaCli.Path -ArgumentList "serve" -WindowStyle Hidden | Out-Null } catch {}
    Start-Sleep -Seconds 2
    $tries = 0
    while ($tries -lt 10 -and -not $running) {
      try {
        Invoke-WebRequest -Uri ($OllamaHost.TrimEnd('/') + "/api/tags") -UseBasicParsing -TimeoutSec 3 | Out-Null
        $running = $true
        break
      } catch { Start-Sleep -Seconds 1; $tries++ }
    }
  }
  try { & $ollamaCli.Path pull $Model } catch {}
}

& $venvPython main.py