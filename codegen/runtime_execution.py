from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen
from pathlib import Path


class RuntimeProjectManager:
    GENERATED_BACKEND_PORT = 8001
    GENERATED_FRONTEND_PORT = 5174

    def __init__(self, root_dir: Path | None = None) -> None:
        self.root_dir = (root_dir or (Path.cwd() / "generated_apps")).resolve()
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.process_registry: dict[str, subprocess.Popen[str] | None] = {
            "backend": None,
            "frontend": None,
        }

    def _backend_health_url(self) -> str:
        return f"http://127.0.0.1:{self.GENERATED_BACKEND_PORT}/health"

    def _frontend_url(self) -> str:
        return f"http://127.0.0.1:{self.GENERATED_FRONTEND_PORT}"

    def _is_port_open(self, port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.5)
            return sock.connect_ex(("127.0.0.1", port)) == 0

    def _wait_for_http(self, url: str, timeout_seconds: float = 30.0) -> bool:
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            try:
                with urlopen(url, timeout=2) as response:
                    if 200 <= getattr(response, "status", 0) < 500:
                        return True
            except URLError:
                time.sleep(0.5)
            except Exception:
                time.sleep(0.5)
        return False

    def create_workspace(self, project_id: str) -> Path:
        safe_project_id = "".join(char for char in project_id if char.isalnum() or char in {"-", "_"}).strip("._-") or "default_project"
        project_path = (self.root_dir / safe_project_id).resolve()
        if self.root_dir not in project_path.parents and project_path != self.root_dir:
            raise ValueError("Unsafe project id")
        project_path.mkdir(parents=True, exist_ok=True)
        return project_path

    def sanitize_path(self, project_path: Path, relative_path: str) -> Path:
        normalized = relative_path.replace("\\", "/").strip("/")
        candidate = (project_path / normalized).resolve()
        if project_path not in candidate.parents and candidate != project_path:
            raise ValueError(f"Unsafe path rejected: {relative_path}")
        return candidate

    def write_files(self, project_path: Path, files: dict[str, str]) -> list[str]:
        written_files: list[str] = []
        for relative_path, content in files.items():
            target = self.sanitize_path(project_path, relative_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            written_files.append(str(target))
        return written_files

    def _detect_stack(self, project_path: Path) -> str:
        if (project_path / "backend" / "main.py").exists():
            return "python"
        if (project_path / "backend" / "server.js").exists():
            return "node"
        raise ValueError("Unable to detect generated project stack")

    def _run_install(self, command: list[str], cwd: Path) -> None:
        subprocess.run(
            command,
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
            timeout=600,
        )

    def _npm_command(self, *args: str) -> list[str]:
        if os.name == "nt":
            return ["cmd", "/c", "npm", *args]
        return ["npm", *args]

    def _node_command(self, *args: str) -> list[str]:
        if os.name == "nt":
            return ["cmd", "/c", "node", *args]
        return ["node", *args]

    def _spawn_process(self, command: list[str], cwd: Path, log_prefix: str) -> subprocess.Popen[str]:
        stdout_log = cwd / f"{log_prefix}.out.log"
        stderr_log = cwd / f"{log_prefix}.err.log"
        stdout_handle = open(stdout_log, "a", encoding="utf-8")
        stderr_handle = open(stderr_log, "a", encoding="utf-8")
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
        return subprocess.Popen(
            command,
            cwd=cwd,
            stdout=stdout_handle,
            stderr=stderr_handle,
            text=True,
            creationflags=creationflags,
        )

    def install_dependencies(self, project_path: Path) -> list[list[str]]:
        commands: list[tuple[list[str], Path]] = []
        stack = self._detect_stack(project_path)
        root_requirements = project_path / "requirements.txt"
        backend_requirements = project_path / "backend" / "requirements.txt"
        frontend_package = project_path / "frontend" / "package.json"
        backend_package = project_path / "backend" / "package.json"

        if stack == "python":
            if root_requirements.exists():
                commands.append(([sys.executable, "-m", "pip", "install", "-r", str(root_requirements)], project_path))
            elif backend_requirements.exists():
                commands.append(([sys.executable, "-m", "pip", "install", "-r", str(backend_requirements)], project_path / "backend"))
            if frontend_package.exists():
                commands.append((self._npm_command("install"), project_path / "frontend"))
        else:
            if backend_package.exists():
                commands.append((self._npm_command("install"), project_path / "backend"))
            if frontend_package.exists():
                commands.append((self._npm_command("install"), project_path / "frontend"))

        for command, cwd in commands:
            self._run_install(command, cwd)

        return [command for command, _ in commands]

    def _stop_process(self, key: str) -> None:
        process = self.process_registry.get(key)
        if not process:
            return
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=15)
        self.process_registry[key] = None

    def start_backend(self, project_path: Path) -> subprocess.Popen[str] | None:
        stack = self._detect_stack(project_path)
        if self._wait_for_http(self._backend_health_url(), timeout_seconds=1.0):
            return self.process_registry.get("backend")
        command = (
            [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", str(self.GENERATED_BACKEND_PORT)]
            if stack == "python"
            else self._node_command("server.js")
        )
        process = self._spawn_process(command, project_path / "backend", "runtime_backend")
        self.process_registry["backend"] = process
        if not self._wait_for_http(self._backend_health_url(), timeout_seconds=25.0):
            raise RuntimeError(
                "Generated backend failed to start on port 8001. Check backend/runtime_backend.err.log for details."
            )
        return process

    def start_frontend(self, project_path: Path) -> subprocess.Popen[str] | None:
        if self._wait_for_http(self._frontend_url(), timeout_seconds=1.0):
            return self.process_registry.get("frontend")
        process = self._spawn_process(
            self._npm_command("run", "dev", "--", "--host", "127.0.0.1", "--port", str(self.GENERATED_FRONTEND_PORT)),
            project_path / "frontend",
            "runtime_frontend",
        )
        self.process_registry["frontend"] = process
        if not self._wait_for_http(self._frontend_url(), timeout_seconds=40.0):
            raise RuntimeError(
                "Generated frontend failed to start on port 5174. Check frontend/runtime_frontend.err.log for details."
            )
        return process

    def restart_backend(self, project_path: Path) -> subprocess.Popen[str] | None:
        self._stop_process("backend")
        return self.start_backend(project_path)

    def restart_frontend(self, project_path: Path) -> subprocess.Popen[str] | None:
        self._stop_process("frontend")
        return self.start_frontend(project_path)

    def get_preview_url(self) -> str:
        return f"http://localhost:{self.GENERATED_FRONTEND_PORT}"

    def get_backend_url(self) -> str:
        return f"http://localhost:{self.GENERATED_BACKEND_PORT}"
