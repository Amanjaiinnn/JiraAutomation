from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


class RuntimeEngine:
    def __init__(self, root_dir: str = "generated_project") -> None:
        self.root_dir = Path(root_dir).resolve()
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.backend_process = None
        self.frontend_process = None

    def _safe_path(self, relative_path: str) -> Path:
        target = (self.root_dir / relative_path).resolve()
        if self.root_dir not in target.parents and target != self.root_dir:
            raise ValueError("Unsafe path")
        return target

    def write_files(self, files: dict[str, str]) -> None:
        for relative_path, content in files.items():
            target = self._safe_path(relative_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")

    def install_dependencies(self) -> None:
        backend_requirements = self.root_dir / "backend" / "requirements.txt"
        if backend_requirements.exists():
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(backend_requirements)], check=False)
        if (self.root_dir / "frontend" / "package.json").exists():
            subprocess.run(["npm", "install"], cwd=self.root_dir / "frontend", check=False)

    def start(self) -> dict[str, str]:
        env = os.environ.copy()
        self.backend_process = subprocess.Popen([sys.executable, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"], cwd=self.root_dir / "backend", env=env)
        self.frontend_process = subprocess.Popen(
            ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5174"],
            cwd=self.root_dir / "frontend",
            env=env,
        )
        return {"backend_url": "http://localhost:8001", "preview_url": "http://localhost:5174"}
