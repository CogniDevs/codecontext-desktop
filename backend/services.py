import os
import sys
import json
import time
import asyncio
import subprocess
import importlib.util
from typing import Tuple, List, Set, Dict, Any, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

codecontext_core = None

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)

pyd_candidates = [
    os.path.join(current_dir, "codecontext_core.pyd"),
    os.path.join(current_dir, "codecontext_core.so"),
    os.path.join(current_dir, "libcodecontext_core.so"),
    os.path.join(current_dir, "libcodecontext_core.dylib"),
    os.path.join(root_dir, "codecontext_core", "target", "release", "codecontext_core.dll"),
    os.path.join(root_dir, "codecontext_core", "target", "release", "codecontext_core.pyd"),
    os.path.join(root_dir, "codecontext_core", "target", "release", "libcodecontext_core.so"),
    os.path.join(root_dir, "codecontext_core", "target", "release", "libcodecontext_core.dylib"),
]

for cand in pyd_candidates:
    if os.path.exists(cand):
        try:
            spec = importlib.util.spec_from_file_location("codecontext_core", cand)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                codecontext_core = mod
                break
        except Exception:
            pass

if codecontext_core is None:
    try:
        if current_dir in sys.path:
            sys.path.remove(current_dir)
        sys.path.insert(0, current_dir)
        import codecontext_core as _mod
        codecontext_core = _mod
    except Exception:
        codecontext_core = None


class RustCoreService:
    @staticmethod
    def is_available() -> bool:
        return codecontext_core is not None and hasattr(codecontext_core, "scan_directory_py")

    @staticmethod
    def scan_directory(root_dir: str, options: dict) -> dict:
        if not RustCoreService.is_available() or not os.path.exists(root_dir):
            return {}
        options_json = json.dumps(options)
        result_json = codecontext_core.scan_directory_py(root_dir, options_json)
        if not result_json or result_json == "null":
            return {}
        return json.loads(result_json)

    @staticmethod
    def count_tokens(text: str) -> int:
        if not RustCoreService.is_available():
            return int(round(len(text) / 3.3)) if text else 0
        return codecontext_core.count_tokens_py(text)

    @staticmethod
    def sanitize_secrets(text: str) -> str:
        if not RustCoreService.is_available():
            return text
        return codecontext_core.sanitize_secrets_py(text)

    @staticmethod
    def strip_comments(text: str, extension: str, rules_json: Optional[str] = None) -> str:
        if not RustCoreService.is_available():
            return text
        return codecontext_core.strip_comments_py(text, extension, rules_json)

    @staticmethod
    def compress_whitespace(text: str) -> str:
        if not RustCoreService.is_available():
            return text
        return codecontext_core.compress_whitespace_py(text)

    @staticmethod
    def trace_dependencies(root_dir: str, target_rel_path: str, content: str) -> List[str]:
        if not RustCoreService.is_available():
            return []
        deps = codecontext_core.trace_dependencies_py(root_dir, target_rel_path, content)
        return list(deps)

    @staticmethod
    def generate_standalone_tree(
        root_name: str,
        root_node: Optional[dict],
        selected_paths: Set[str],
        xml_format: bool
    ) -> str:
        if not RustCoreService.is_available():
            return ""
        root_node_json = json.dumps(root_node) if root_node else ""
        selected_paths_json = json.dumps(list(selected_paths))
        return codecontext_core.generate_standalone_tree_py(
            root_name,
            root_node_json,
            selected_paths_json,
            xml_format
        )

    @staticmethod
    def build_payload(
        root_name: str,
        root_node: Optional[dict],
        files: List[Tuple[str, str]],
        selected_paths: Set[str],
        options: dict
    ) -> str:
        if not RustCoreService.is_available():
            return ""
        root_node_json = json.dumps(root_node) if root_node else ""
        files_json = json.dumps(files)
        selected_paths_json = json.dumps(list(selected_paths))
        options_json = json.dumps(options)
        return codecontext_core.build_payload_py(
            root_name,
            root_node_json,
            files_json,
            selected_paths_json,
            options_json
        )


class GitService:
    @staticmethod
    def is_git_repository(root_dir: str) -> bool:
        if not root_dir or not os.path.exists(root_dir):
            return False
        git_dir = os.path.join(root_dir, '.git')
        if os.path.exists(git_dir):
            return True
        try:
            flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            res = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=root_dir,
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                creationflags=flags
            )
            return res.returncode == 0 and res.stdout.strip() == "true"
        except Exception:
            return False

    @staticmethod
    def get_modified_files(root_dir: str) -> Tuple[bool, str, List[str]]:
        if not root_dir or not os.path.exists(root_dir):
            return False, "Папка проекта не найдена", []

        try:
            flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            res = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=root_dir,
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                check=True,
                creationflags=flags
            )
            modified_files: Set[str] = set()
            for line in res.stdout.splitlines():
                if len(line) > 3:
                    path_part = line[3:].strip()
                    if " -> " in path_part:
                        path_part = path_part.split(" -> ")[-1].strip()
                    path_part = path_part.strip('"\'')
                    normalized_path = path_part.replace('\\', '/')
                    modified_files.add(normalized_path)

            sorted_files = sorted(list(modified_files))
            if not sorted_files:
                return False, "Нет измененных файлов в репозитории Git", []

            return True, f"Найдено {len(sorted_files)} измененных файлов", sorted_files
        except FileNotFoundError:
            return False, "Git CLI не установлен в операционной системе", []
        except Exception as e:
            return False, f"Ошибка Git: {str(e)}", []

    @staticmethod
    def get_git_diff(root_dir: str, context_lines: int = 3) -> Tuple[bool, str]:
        if not root_dir or not os.path.exists(root_dir):
            return False, "Папка проекта не найдена"

        try:
            flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            res = subprocess.run(
                ["git", "diff", f"-U{max(0, context_lines)}"],
                cwd=root_dir,
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                check=True,
                creationflags=flags
            )
            diff_text = res.stdout.strip()
            if not diff_text:
                return False, "Нет изменений для построения Git Diff"

            return True, diff_text
        except FileNotFoundError:
            return False, "Git CLI не установлен в операционной системе"
        except Exception as e:
            return False, f"Ошибка построения Git Diff: {str(e)}"


class FileChangeEventHandler(FileSystemEventHandler):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback
        self.ignored_segments = {
            '.git', '.idea', '.vscode', 'node_modules', '__pycache__',
            '.venv', 'venv', 'dist', 'build', 'target', '.angular', 'icon_data.py'
        }

    def on_any_event(self, event):
        path_parts = set(event.src_path.replace('\\', '/').split('/'))
        if not path_parts.intersection(self.ignored_segments):
            self.callback(event.src_path)


class ProjectWatcherService:
    def __init__(self):
        self.observer: Optional[Observer] = None
        self.current_path: Optional[str] = None
        self.event_queues: List[asyncio.Queue] = []
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.last_emit_time = 0.0
        self.debounce_seconds = 0.3

    def set_event_loop(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop

    def register_listener(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        self.event_queues.append(q)
        return q

    def unregister_listener(self, q: asyncio.Queue):
        if q in self.event_queues:
            self.event_queues.remove(q)

    def _on_file_changed(self, file_path: str):
        now = time.time()
        if now - self.last_emit_time < self.debounce_seconds:
            return
        self.last_emit_time = now

        target_loop = self.loop
        if target_loop is None or target_loop.is_closed():
            try:
                target_loop = asyncio.get_running_loop()
            except RuntimeError:
                return

        for q in list(self.event_queues):
            try:
                asyncio.run_coroutine_threadsafe(
                    q.put({"type": "change", "path": file_path, "timestamp": now}),
                    target_loop
                )
            except Exception:
                pass

    def start_watching(self, path: str):
        self.stop_watching()
        if not path or not os.path.exists(path):
            return

        self.current_path = path
        self.observer = Observer()
        self.observer.daemon = True
        handler = FileChangeEventHandler(self._on_file_changed)
        try:
            self.observer.schedule(handler, self.current_path, recursive=True)
            self.observer.start()
        except Exception:
            self.observer = None

    def stop_watching(self):
        if self.observer:
            try:
                self.observer.stop()
                self.observer.join(timeout=0.5)
            except Exception:
                pass
            self.observer = None
            self.current_path = None


watcher_service = ProjectWatcherService()