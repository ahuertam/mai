# MAI — Agente local de tareas

MAI es una IA local que recibe tareas en texto, genera un plan ejecutable y las ejecuta en Windows, dando feedback directamente en la ventana de comandos. Usa modelos gratuitos a través de [Ollama](https://ollama.com) y se puede extender con LiveKit para interacción por voz en tiempo real.

## Requisitos

- Windows con PowerShell
- Python 3.10+
- Ollama instalado y en ejecución
- Librería de Python `ollama`: `pip install ollama`

## Instalación

- Instalación rápida (PowerShell):
  - `powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1`
  - Crea `.venv`, instala `ollama`, intenta descargar `llama3.1:8b` y comprueba Ollama.
  - Si tu política de ejecución bloquea scripts: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`.

- Instalación desde Bash/WSL/Git Bash:
  - `bash ./install.sh`
  - Detecta `python`/`python3`/`py`, crea `.venv`, instala `ollama` y prueba `ollama pull`.

- Instalación manual (alternativa):
  - Instala Ollama desde https://ollama.com y arráncalo.
  - Descarga un modelo: `ollama pull llama3.1:8b` (o `qwen2.5:7b`, `mistral-nemo:latest`).
  - Crea entorno: `python -m venv .venv`.
  - Instala lib: `.\.venv\Scripts\python.exe -m pip install --upgrade pip ollama`.

## Uso

- Iniciar MAI:
  - PowerShell: `.\.venv\Scripts\python.exe main.py`
  - Bash (WSL/Linux/macOS): `.venv/bin/python main.py`

- Escribe tareas en la consola. Ejemplos:
  - `Crear un archivo README sencillo en el directorio actual`
  - `Listar procesos en ejecución con PowerShell`
  - `Escribir "Hola MAI" en output.txt y mostrar su contenido`

- Salir: `exit` o `quit`.

### Modo directo (sin Ollama)

- Usa prefijos para ejecutar acciones directamente:
  - `shell: <comando PowerShell>`
  - `read: <ruta>`
  - `write: <ruta> | <contenido>`
  - `echo: <texto>`
  - `open: <url>`
  - `get: <url> | <ruta>` (guarda en archivo si se indica `ruta`)
  - `status` (muestra estado de Ollama y modelo configurado)
  - `download` o `download: <modelo>` (descarga el modelo)

- Ejemplos:
  - `shell: Get-Process | Select-Object -First 3`
  - `read: README.md`
  - `write: output.txt | Hola MAI`
  - `echo: Listo`
  - `open: https://www.microsoft.com`
  - `get: https://example.com | downloads/example.html`
  - `status`
  - La salida incluye: `host`, `server si/no`, `cli` (versión del CLI), `model` y `size` del modelo si está descargado.
  - Si el modelo no está presente y el servidor está activo, se sugiere usar `download`.

## Configuración

- Cambia el modelo por defecto con la variable de entorno:
  - `setx MAI_MODEL "llama3.1:8b"`
  - Alternativa local: crea `.env` con `MAI_MODEL=...` y `OLLAMA_HOST=...`

- Comprobación de Ollama:
  - CLI: `ollama pull llama3.1:8b`
  - Servicio: visita `http://localhost:11434` o usa `curl http://localhost:11434/api/tags`
- Acciones soportadas por el ejecutor:
  - `shell`: ejecuta comandos en PowerShell, captura `stdout` y `stderr`.
  - `file_write`: escribe contenido en una ruta relativa al proyecto.
  - `file_read`: lee y muestra contenido de una ruta relativa.

## Modelos gratuitos recomendados

- `llama3.1:8b` — equilibrio general
- `qwen2.5:7b` — buen seguimiento de formato y razonamiento
- `mistral-nemo:latest` — alternativa competente

## Seguridad y límites

- Las acciones están restringidas a un conjunto pequeño y controlado.
- Rutas de archivo se resuelven dentro del directorio actual.
- Los planes deben ser JSON estricto; acciones desconocidas se ignoran con aviso.

## Integración LiveKit (opcional)

- Objetivo: control por voz y presencia en sala, enviando transcripciones como tareas a MAI.
- Enfoques:
  - Python: `livekit-agents` para entrada/salida de audio y eventos.
  - Node: `@livekit/agents` para una interfaz similar.
- Diseño: un módulo que escuche texto (voz a texto) y llame a `enqueue(...)` de MAI.

## Estructura

- `main.py` — agente, planificador (Ollama) y ejecutor con cola de tareas.
- `todo.md` — mejoras opcionales y hoja de ruta sugerida.

## Próximos pasos

Consulta `todo.md` para ver las mejoras propuestas (memoria de sesión, validación de pasos, nuevas herramientas, observabilidad, LiveKit, etc.).

## Casos de uso

- Automatización local de tareas
  - Ejecuta comandos de sistema, crea/lee/escribe archivos, abre URLs y descarga contenido.
  - Ejemplos rápidos:
    - Natural: "Crea un archivo `output.txt` con el texto Hola MAI y muéstrame su contenido".
    - Directo: `write: output.txt | Hola MAI` seguido de `read: output.txt`.
    - Sistema: `shell: Get-Process | Select-Object -First 5`.

- Desarrollo y DevOps
  - Preparación de entorno, ejecución de tests y builds, linting, scripts de CI locales.
  - Natural: "Ejecuta los tests y muéstrame los errores".
  - Directo: `shell: .\.venv\Scripts\python.exe -m pytest -q`.
  - Beneficio: feedback continuo en consola y posibilidad de planificar pasos con LLM cuando Ollama está activo.

- Mantenimiento y observabilidad
  - Verificar servicios, revisar registros, medir tiempos y estado del sistema.
  - Directo: `status` para ver Ollama y modelo; `read: logs/app.log`.
  - Beneficio: acciones acotadas y controladas, sin exponer el sistema innecesariamente.

- Recuperación de información online
  - Traer páginas para referencia rápida sin salir de tu entorno.
  - Directo: `get: https://example.com` o `get: https://example.com | downloads/example.html`.
  - Beneficio: combinar conocimiento online con ejecución local.

- Operación por voz (LiveKit)
  - Integrar LiveKit para dictar tareas y recibir respuestas en tiempo real.
  - Beneficio: manos libres con ejecución local (la lógica y acciones siguen en tu máquina).

## Cómo ayuda en tu sistema

- Local y seguro
  - Las acciones están limitadas a un conjunto pequeño: `shell`, `file_write`, `file_read`, `open`, `get`, `status`, `download`.
  - Operan sobre el directorio actual y rutas relativas; evita efectos colaterales no deseados.

- Flujo dual (natural y directo)
  - Natural (con LLM): describe tareas en lenguaje humano y MAI planifica y ejecuta.
  - Directo (sin LLM): usa prefijos para control explícito y rápido.
  - El comando `status` muestra si el servidor y el modelo están listos; `download` permite bajar el modelo al vuelo.

- Extensible
  - Se pueden añadir más acciones (copiar/mover archivos, HTTP avanzado, búsqueda web) y validaciones.
  - Integración con LiveKit para orquestación por voz.

## Ejemplos relevantes

- Preparar entorno de trabajo
  - PowerShell: `powershell -NoProfile -ExecutionPolicy Bypass -File .\run.ps1`.
  - Bash: `MODEL="llama3.1:8b" OLLAMA_HOST="http://localhost:11434" bash ./run.sh`.

- Ver estado y descargar modelo
  - `status` → muestra `host`, `server si/no`, `cli`, `model`, `size`.
  - Si `present=no` y `server=si`: `download` o `download: qwen2.5:7b`.

- Automatizar una tarea mixta
  - "Lista los 5 procesos con más memoria, guarda el resultado en `proc.txt` y ábrelo".
  - Directo equivalente:
    - `shell: Get-Process | Sort-Object WS -Descending | Select-Object -First 5 | Tee-Object -FilePath proc.txt`
    - `open: proc.txt`

## Mini guía de buenas prácticas

- Mantén configuración en `.env`
  - Define `MAI_MODEL` y `OLLAMA_HOST` ahí para tener un arranque consistente.
  - Usa `run.ps1` / `run.sh` para respetar `.env` automáticamente.

- Prefiere rutas relativas al proyecto
  - `file_write` y `file_read` operan desde el directorio actual; evita rutas absolutas que puedan afectar otras áreas del sistema.
  - Organiza salidas en carpetas como `outputs/` o `downloads/`.

- Usa el flujo adecuado según disponibilidad
  - Con LLM activo: describe tareas en lenguaje natural y deja que MAI planifique.
  - Sin LLM: usa prefijos directos (`shell`, `read`, `write`, `open`, `get`, `status`, `download`) para control explícito.

- Valida antes de ejecutar comandos sensibles
  - Revisa y confirma comandos que puedan modificar el sistema (instalaciones, cambios en servicios, borrado de archivos).
  - Si dudas, usa primero `read:` o `get:` para inspeccionar información.

- Comprueba estado y prepara el modelo
  - `status` para ver si el servidor Ollama está activo y si el modelo está presente.
  - Usa `download` o `download: <modelo>` cuando falte el modelo.

- Mantén feedback visible
  - El modo `shell` imprime salida en streaming (`stdout>`), útil para tareas largas.
  - Si el comando produce errores, revisa `stderr>` y corrige parámetros.

## Troubleshooting

- Ollama no responde
  - Verifica el endpoint: `Invoke-WebRequest -Uri http://localhost:11434/api/tags -UseBasicParsing` (debe devolver 200).
  - Inicia el servicio: PowerShell `ollama serve` o usa `run.ps1`/`run.sh`.
  - Cortafuegos: permite a Ollama escuchar en `localhost`.

- Modelo no presente
  - Comprueba: `ollama list`.
  - Descarga: `download` o `download: llama3.1:8b` desde MAI, o `ollama pull llama3.1:8b` manual.
  - Cambia modelo en `.env`: `MAI_MODEL=qwen2.5:7b` y relanza.

- Scripts bloqueados en Windows
  - Permite ejecución en la sesión: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`.
  - Ejecuta: `powershell -NoProfile -ExecutionPolicy Bypass -File .\run.ps1`.

- CLI de Ollama no encontrado
  - Instala en Windows: `https://ollama.com/download` (requiere Windows 10+).
  - En Linux/macOS: `curl -fsSL https://ollama.com/install.sh | sh` o `brew install ollama`.

- Variables de entorno no aplicadas
  - Usa `.env` en el directorio del proyecto; `run.ps1` y `run.sh` lo cargan automáticamente.
  - Verifica dentro de MAI: `status` muestra `host` y modelo.

- Salida tarda en verse
  - `shell` imprime `stdout>` en streaming; si el comando no escribe líneas, la salida aparecerá al finalizar.
  - Para ver errores, revisa `stderr>` al final o usa comandos con salida por línea.