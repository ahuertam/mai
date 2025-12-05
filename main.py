import json
import os
import threading
import queue
import subprocess
from typing import Any, Dict, List
import urllib.request
import urllib.error
import re
from datetime import datetime

try:
    import ollama
except ImportError:
    ollama = None


def load_env():
    path = os.path.join(os.getcwd(), ".env")
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        os.environ[k.strip()] = v.strip()
        except Exception:
            pass

class Planner:
    def __init__(self, model: str = "llama3.1:8b"):
        self.model = model
        self.ollama_host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

    def ensure(self):
        if ollama is None:
            raise RuntimeError("Instala el paquete 'ollama' con 'pip install ollama' y ten Ollama en ejecución")

    def _server_up(self) -> bool:
        try:
            url = f"{self.ollama_host.rstrip('/')}/api/tags"
            with urllib.request.urlopen(url, timeout=3) as r:
                return 200 <= getattr(r, "status", 200) < 300
        except Exception:
            return False

    def plan(self, task_text: str) -> Dict[str, Any]:
        self.ensure()
        prompt = (
            "Eres un agente que genera un plan ejecutable para una tarea. "
            "Devuelve solo JSON con la forma: {\"objective\": str, \"steps\": [ {\"action\": str, ... } ] }. "
            "Acciones permitidas: \"shell\" (campo \"command\" de PowerShell), \"file_write\" (\"path\", \"content\"), \"file_read\" (\"path\"). "
            "No uses acciones que no existan. No expliques nada fuera del JSON. "
            f"Tarea: {task_text}"
        )
        try:
            self.ensure()
            if not self._server_up():
                raise RuntimeError("Ollama no disponible")
            models = []
            try:
                lm = ollama.list()
                models = lm.get("models", []) if isinstance(lm, dict) else []
            except Exception:
                models = []
            names = []
            for m in models:
                n = None
                if isinstance(m, dict):
                    n = m.get("model") or m.get("name")
                if n:
                    names.append(n)
            if self.model not in names:
                try:
                    print(f"[MAI] Descargando modelo {self.model}...", flush=True)
                    ollama.pull(self.model)
                except Exception as e:
                    raise RuntimeError(f"Modelo no disponible: {e}")
            res = ollama.chat(model=self.model, messages=[{"role": "user", "content": prompt}])
            txt = res.get("message", {}).get("content", "{}")
            return json.loads(txt)
        except Exception as e:
            reason = str(e)
            try:
                reason = re.sub(r"[^\w\-\.:/ ]", "", reason)
            except Exception:
                pass
            return {
                "objective": task_text,
                "steps": [
                    {"action": "shell", "command": f"Write-Host MAI fallo LLM: {reason}"}
                ],
            }


class DirectPlanner:
    def plan(self, task_text: str) -> Dict[str, Any] | None:
        t = task_text.strip()
        t = t.replace("`", "").replace("“", '"').replace("”", '"')
        m = re.match(r"^(shell|sh|ps)\s*:\s*(.+)$", t, re.IGNORECASE)
        if m:
            cmd = m.group(2).strip()
            return {"objective": t, "steps": [{"action": "shell", "command": cmd}]}
        m = re.match(r"^(read|cat)\s*:\s*(.+)$", t, re.IGNORECASE)
        if m:
            path = m.group(2).strip()
            return {"objective": t, "steps": [{"action": "file_read", "path": path}]}
        m = re.match(r"^(write)\s*:\s*([^|]+?)(?:\|\s*(.+))?$", t, re.IGNORECASE)
        if m:
            path = m.group(2).strip()
            content = (m.group(3) or "").strip()
            return {"objective": t, "steps": [{"action": "file_write", "path": path, "content": content}]}
        m = re.match(r"^(echo)\s*:\s*(.+)$", t, re.IGNORECASE)
        if m:
            msg = m.group(2).strip()
            return {"objective": t, "steps": [{"action": "shell", "command": f"Write-Host \"{msg}\""}]}
        m = re.match(r"^(open)\s*:\s*(.+)$", t, re.IGNORECASE)
        if m:
            url = m.group(2).strip()
            return {"objective": t, "steps": [{"action": "open_url", "url": url}]}
        m = re.match(r"^(get|download)\s*:\s*([^|]+?)(?:\|\s*(.+))?$", t, re.IGNORECASE)
        if m:
            url = m.group(2).strip()
            path = (m.group(3) or None)
            if path:
                path = path.strip()
            return {"objective": t, "steps": [{"action": "http_get", "url": url, "path": path}]}
        m = re.match(r"^(status)\s*:?\s*$", t, re.IGNORECASE)
        if m:
            return {"objective": t, "steps": [{"action": "status"}]}
        m = re.match(r"^(download)\s*:?\s*(.+)?$", t, re.IGNORECASE)
        if m:
            name = (m.group(2) or "").strip()
            return {"objective": t, "steps": [{"action": "download", "model": name if name else None}]}
        return None


class RouterPlanner:
    def __init__(self, llm: Planner, direct: DirectPlanner):
        self.llm = llm
        self.direct = direct

    def plan(self, task_text: str) -> Dict[str, Any]:
        d = self.direct.plan(task_text)
        if d is not None:
            return d
        return self.llm.plan(task_text)


class Executor:
    def __init__(self):
        pass

    def run_shell(self, command: str) -> Dict[str, Any]:
        try:
            p = subprocess.Popen(
                ["powershell", "-NoProfile", "-Command", command],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            stdout_buf: List[str] = []
            stderr_buf: List[str] = []
            assert p.stdout is not None
            for line in iter(p.stdout.readline, ""):
                if line == "" and p.poll() is not None:
                    break
                stdout_buf.append(line)
                print(f"[MAI] stdout> {line}", end="", flush=True)
            p.wait(timeout=1800)
            if p.stderr is not None:
                err = p.stderr.read() or ""
                if err:
                    stderr_buf.append(err)
                    print(f"[MAI] stderr> {err}", flush=True)
            return {"ok": p.returncode == 0, "stdout": "".join(stdout_buf), "stderr": "".join(stderr_buf), "code": p.returncode}
        except Exception as e:
            return {"ok": False, "stdout": "", "stderr": str(e), "code": -1}

    def file_write(self, path: str, content: str) -> Dict[str, Any]:
        try:
            base = os.getcwd()
            abs_path = os.path.abspath(os.path.join(base, path))
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(content)
            return {"ok": True, "path": abs_path}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def file_read(self, path: str) -> Dict[str, Any]:
        try:
            base = os.getcwd()
            abs_path = os.path.abspath(os.path.join(base, path))
            with open(abs_path, "r", encoding="utf-8") as f:
                data = f.read()
            return {"ok": True, "path": abs_path, "content": data}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def http_get(self, url: str, path: str | None = None) -> Dict[str, Any]:
        try:
            with urllib.request.urlopen(url, timeout=15) as r:
                data = r.read()
            if path:
                base = os.getcwd()
                abs_path = os.path.abspath(os.path.join(base, path))
                os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                with open(abs_path, "wb") as f:
                    f.write(data)
                return {"ok": True, "path": abs_path}
            else:
                try:
                    text = data.decode("utf-8", errors="replace")
                except Exception:
                    text = ""
                return {"ok": True, "content": text}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def open_url(self, url: str) -> Dict[str, Any]:
        cmd = f"Start-Process '{url}'"
        return self.run_shell(cmd)

    def status(self, host: str, model: str) -> Dict[str, Any]:
        server = False
        try:
            with urllib.request.urlopen(f"{host.rstrip('/')}/api/tags", timeout=3) as r:
                server = 200 <= getattr(r, "status", 200) < 300
        except Exception:
            server = False
        models = []
        present = False
        model_size_bytes = None
        cli_version = ""
        try:
            p = subprocess.run(["ollama", "--version"], capture_output=True, text=True, timeout=5)
            cli_version = (p.stdout or p.stderr or "").strip()
        except Exception:
            cli_version = ""
        try:
            if ollama is not None:
                lm = ollama.list()
                arr = lm.get("models", []) if isinstance(lm, dict) else []
                for m in arr:
                    n = None
                    if isinstance(m, dict):
                        n = m.get("model") or m.get("name")
                        if n == model:
                            model_size_bytes = m.get("size") or m.get("size_bytes") or (m.get("details", {}) or {}).get("size")
                    if n:
                        models.append(n)
                present = model in models
        except Exception:
            pass
        def human(n):
            try:
                n = int(n)
            except Exception:
                return ""
            units = ["B", "KB", "MB", "GB", "TB"]
            i = 0
            f = float(n)
            while f >= 1024 and i < len(units) - 1:
                f /= 1024.0
                i += 1
            return f"{f:.1f} {units[i]}"
        return {"server": server, "host": host, "model": model, "model_present": present, "models": models, "cli_version": cli_version, "model_size_bytes": model_size_bytes, "model_size_human": human(model_size_bytes) if model_size_bytes is not None else ""}

    def download_model(self, model: str) -> Dict[str, Any]:
        try:
            if ollama is None:
                return {"ok": False, "error": "ollama lib no disponible"}
            print(f"[MAI] Descargando modelo {model}...", flush=True)
            ollama.pull(model)
            return {"ok": True, "model": model}
        except Exception as e:
            return {"ok": False, "error": str(e)}


class MAI:
    def __init__(self, model: str | None = None):
        self.model = model or os.environ.get("MAI_MODEL", "llama3.1:8b")
        self.planner = RouterPlanner(Planner(self.model), DirectPlanner())
        self.executor = Executor()
        self.q: "queue.Queue[Dict[str, Any]]" = queue.Queue()
        self.worker = threading.Thread(target=self._work_loop, daemon=True)
        self.running = False

    def start(self):
        self.running = True
        self.worker.start()

    def stop(self):
        self.running = False

    def enqueue(self, text: str):
        try:
            os.makedirs("logs", exist_ok=True)
            d = datetime.now()
            fn = f"interactions-{d.strftime('%Y%m%d')}.log"
            with open(os.path.join("logs", fn), "a", encoding="utf-8") as f:
                f.write(f"{d.isoformat()} | {text}\n")
        except Exception:
            pass
        self.q.put({"text": text})

    def _work_loop(self):
        while self.running:
            try:
                item = self.q.get(timeout=0.5)
            except queue.Empty:
                continue
            txt = item.get("text", "")
            print(f"[MAI] Planificando: {txt}", flush=True)
            plan = self.planner.plan(txt)
            steps: List[Dict[str, Any]] = plan.get("steps", [])
            print(f"[MAI] Objetivo: {plan.get('objective', '')}", flush=True)
            for i, step in enumerate(steps, 1):
                action = step.get("action")
                print(f"[MAI] Ejecutando paso {i}: {action}", flush=True)
                if action == "shell":
                    res = self.executor.run_shell(step.get("command", ""))
                    if res.get("stderr"):
                        print(f"[MAI] stderr:\n{res.get('stderr','')}", flush=True)
                    try:
                        os.makedirs("logs", exist_ok=True)
                        d = datetime.now()
                        fn = f"steps-{d.strftime('%Y%m%d')}.log"
                        with open(os.path.join("logs", fn), "a", encoding="utf-8") as f:
                            f.write(f"{d.isoformat()} | shell | code={res.get('code')} | ok={res.get('ok')}\n")
                            if res.get("stdout"):
                                f.write(f"stdout:\n{res.get('stdout')}\n")
                            if res.get("stderr"):
                                f.write(f"stderr:\n{res.get('stderr')}\n")
                    except Exception:
                        pass
                elif action == "file_write":
                    res = self.executor.file_write(step.get("path", "output.txt"), step.get("content", ""))
                    print(f"[MAI] write: {res}", flush=True)
                    try:
                        os.makedirs("logs", exist_ok=True)
                        d = datetime.now()
                        fn = f"steps-{d.strftime('%Y%m%d')}.log"
                        with open(os.path.join("logs", fn), "a", encoding="utf-8") as f:
                            f.write(f"{d.isoformat()} | file_write | path={step.get('path','')} | ok={res.get('ok')}\n")
                    except Exception:
                        pass
                elif action == "file_read":
                    res = self.executor.file_read(step.get("path", ""))
                    if res.get("ok"):
                        print(f"[MAI] file content ({res.get('path','')}):\n{res.get('content','')}", flush=True)
                    else:
                        print(f"[MAI] error: {res}", flush=True)
                    try:
                        os.makedirs("logs", exist_ok=True)
                        d = datetime.now()
                        fn = f"steps-{d.strftime('%Y%m%d')}.log"
                        with open(os.path.join("logs", fn), "a", encoding="utf-8") as f:
                            f.write(f"{d.isoformat()} | file_read | path={step.get('path','')} | ok={res.get('ok')}\n")
                    except Exception:
                        pass
                elif action == "http_get":
                    res = self.executor.http_get(step.get("url", ""), step.get("path"))
                    if res.get("ok") and res.get("content"):
                        print(f"[MAI] http content:\n{res.get('content','')}", flush=True)
                    else:
                        print(f"[MAI] http result: {res}", flush=True)
                    try:
                        os.makedirs("logs", exist_ok=True)
                        d = datetime.now()
                        fn = f"steps-{d.strftime('%Y%m%d')}.log"
                        with open(os.path.join("logs", fn), "a", encoding="utf-8") as f:
                            f.write(f"{d.isoformat()} | http_get | url={step.get('url','')} | ok={res.get('ok')} | path={step.get('path')}\n")
                    except Exception:
                        pass
                elif action == "open_url":
                    res = self.executor.open_url(step.get("url", ""))
                    print(f"[MAI] open url: {res}", flush=True)
                    try:
                        os.makedirs("logs", exist_ok=True)
                        d = datetime.now()
                        fn = f"steps-{d.strftime('%Y%m%d')}.log"
                        with open(os.path.join("logs", fn), "a", encoding="utf-8") as f:
                            f.write(f"{d.isoformat()} | open_url | url={step.get('url','')} | ok={res.get('ok')}\n")
                    except Exception:
                        pass
                elif action == "status":
                    host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
                    res = self.executor.status(host, self.model)
                    print(f"[MAI] status: host={res.get('host')} server={'si' if res.get('server') else 'no'} cli={res.get('cli_version')} model={res.get('model')} present={'si' if res.get('model_present') else 'no'} size={res.get('model_size_human')}", flush=True)
                    if res.get('server') and not res.get('model_present'):
                        print(f"[MAI] El modelo no está descargado. Escribe 'download' para descargar {self.model} o 'download: <modelo>'", flush=True)
                    try:
                        os.makedirs("logs", exist_ok=True)
                        d = datetime.now()
                        fn = f"steps-{d.strftime('%Y%m%d')}.log"
                        with open(os.path.join("logs", fn), "a", encoding="utf-8") as f:
                            f.write(f"{d.isoformat()} | status | host={host} server={'si' if res.get('server') else 'no'} model_present={'si' if res.get('model_present') else 'no'}\n")
                    except Exception:
                        pass
                else:
                    print(f"[MAI] Acción desconocida: {action}", flush=True)
            print("[MAI] Tarea terminada", flush=True)


def main():
    load_env()
    model = os.environ.get("MAI_MODEL", "llama3.1:8b")
    status_checker = Planner(model)
    host = status_checker.ollama_host
    available = status_checker._server_up()
    print(f"[MAI] OLLAMA_HOST: {host}", flush=True)
    print(f"[MAI] Ollama activo: {'si' if available else 'no'}", flush=True)
    agent = MAI(model=model)
    agent.start()
    print(f"[MAI] Modelo: {model}", flush=True)
    print("[MAI] Escribe tareas. 'exit' para salir.", flush=True)
    print("[MAI] Modo directo: 'shell:<cmd>' | 'read:<ruta>' | 'write:<ruta> | <contenido>' | 'echo:<texto>'", flush=True)
    while True:
        try:
            t = input("> ")
        except EOFError:
            break
        if not t:
            continue
        if t.strip().lower() in {"exit", "quit"}:
            break
        agent.enqueue(t)
    agent.stop()


if __name__ == "__main__":
    main()