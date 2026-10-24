import os
import sys
import json
import asyncio
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query
from sse_starlette.sse import EventSourceResponse

try:
    import webview
except ImportError:
    webview = None

from backend.config import config_manager
from backend.schemas import (
    FileNode, ScanRequest, ScanOptions,
    PayloadRequest, PayloadResponse,
    StandaloneTreeRequest, StandaloneTreeResponse,
    GitStatusRequest, GitStatusResponse,
    GitDiffRequest, GitDiffResponse,
    DependenciesRequest, DependenciesResponse,
    TokenCountRequest, TokenCountResponse,
    PromptPreset, CustomRuleRequest,
    CompilePromptRequest, CompilePromptResponse,
    SaveFileRequest, SaveFileResponse,
    ServiceStatus
)
from backend.services import RustCoreService, GitService, watcher_service

api_router = APIRouter(prefix="/api")


@api_router.get("/status", response_model=ServiceStatus)
async def get_status():
    return ServiceStatus(
        status="online",
        desktop_bridge=True,
        rust_engine_available=RustCoreService.is_available(),
        current_version="2.0.0",
        system_platform=sys.platform
    )


@api_router.post("/select-folder")
async def select_folder_endpoint():
    try:
        if webview and webview.windows:
            window = webview.windows[0]
            result = window.create_file_dialog(webview.FOLDER_DIALOG)
            if result and len(result) > 0:
                selected_path = result[0]
                return {"success": True, "path": selected_path}
        return {"success": False, "path": ""}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка диалога: {str(e)}")


@api_router.post("/select-save-file")
async def select_save_file_endpoint(req: Optional[Dict[str, Any]] = None):
    try:
        default_filename = ""
        file_types: tuple = ()
        if req:
            default_filename = req.get("default_filename", "")
            ext = req.get("extension", "").lower().strip(".")
            if ext == "xml":
                file_types = ("XML Files (*.xml)", "All Files (*.*)")
            elif ext == "txt":
                file_types = ("Text Files (*.txt)", "All Files (*.*)")

        if webview and webview.windows:
            window = webview.windows[0]
            result = window.create_file_dialog(
                webview.SAVE_DIALOG,
                save_filename=default_filename,
                file_types=file_types
            )
            if result:
                save_path = result if isinstance(result, str) else result[0] if len(result) > 0 else ""
                if save_path:
                    return {"success": True, "path": save_path}
        return {"success": False, "path": ""}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка диалога сохранения: {str(e)}")


@api_router.get("/gitignore")
async def get_gitignore_rules_endpoint(root_dir: str = Query(...)):
    if not root_dir or not os.path.exists(root_dir):
        return {"rules": []}
    git_file = os.path.join(root_dir, ".gitignore")
    if not os.path.isfile(git_file):
        return {"rules": []}
    try:
        rules: List[str] = []
        with open(git_file, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                trimmed = line.strip()
                if not trimmed or trimmed.startswith("#"):
                    continue
                if " #" in trimmed:
                    trimmed = trimmed.split(" #")[0].strip()
                if trimmed:
                    rules.append(trimmed)
        return {"rules": rules}
    except Exception:
        return {"rules": []}


@api_router.post("/scan", response_model=Dict[str, Any])
async def scan_directory_endpoint(req: ScanRequest):
    if not os.path.exists(req.root_dir):
        raise HTTPException(status_code=404, detail="Указанная папка проекта не найдена")

    raw_options = req.options.model_dump() if req.options else config_manager.settings
    options = {
        "use_gitignore": raw_options.get("use_gitignore", True),
        "ignore_binary": raw_options.get("ignore_binary", True),
        "ignore_lockfiles": raw_options.get("ignore_lockfiles", True),
        "whitelist_extensions": raw_options.get("whitelist_extensions", raw_options.get("active_extensions", [])),
        "manual_excludes": raw_options.get("manual_excludes", raw_options.get("global_excludes", [])),
        "gitignore_disabled_rules": raw_options.get("gitignore_disabled_rules", []),
        "binary_extensions": raw_options.get("binary_extensions", config_manager.default_settings.get("binary_extensions", [])),
        "lockfiles_excludes": raw_options.get("lockfiles_excludes", config_manager.default_settings.get("lockfiles_excludes", [])),
        "output_file_path": raw_options.get("output_file_path", None)
    }

    try:
        result = RustCoreService.scan_directory(req.root_dir, options)
        if config_manager.get_setting("auto_watch", True):
            loop = asyncio.get_running_loop()
            watcher_service.set_event_loop(loop)
            watcher_service.start_watching(req.root_dir)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка сканирования Rust: {str(e)}")


@api_router.post("/payload", response_model=PayloadResponse)
async def build_payload_endpoint(req: PayloadRequest):
    files_payload: List[tuple] = []

    if req.custom_files:
        for cf in req.custom_files:
            files_payload.append((cf.rel_path, cf.content))
    elif not req.options.git_diff_mode and req.root_dir:
        for rel_path in req.selected_paths:
            full_path = os.path.join(req.root_dir, rel_path)
            file_name = os.path.basename(rel_path).lower()
            if file_name == "icon_data.py" or file_name.endswith("_data.py"):
                files_payload.append((rel_path, f"[Auto-generated base64 asset file '{file_name}' omitted]"))
                continue
            if os.path.isfile(full_path):
                try:
                    with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                        files_payload.append((rel_path, f.read()))
                except Exception as e:
                    files_payload.append((rel_path, f"[Ошибка чтения: {str(e)}]"))

    git_diff_text = None
    if req.options.git_diff_mode and req.root_dir:
        success, diff_res = GitService.get_git_diff(req.root_dir, req.options.git_diff_context_lines)
        if success:
            git_diff_text = diff_res

    comment_rules_json = None
    if config_manager.comment_rules:
        comment_rules_json = json.dumps(config_manager.comment_rules)

    options = {
        "strip_comments": req.options.strip_comments,
        "compress_whitespace": req.options.compress_whitespace,
        "sanitize_secrets": req.options.sanitize_secrets,
        "skeleton_mode": req.options.skeleton_mode,
        "xml_format": req.options.xml_format,
        "always_send_full_tree": req.options.always_send_full_tree,
        "system_prompt": req.options.system_prompt,
        "comment_rules_json": comment_rules_json,
        "max_token_budget": req.options.max_token_budget,
        "git_diff_mode": req.options.git_diff_mode,
        "git_diff_context_lines": req.options.git_diff_context_lines,
        "git_diff_text": git_diff_text
    }

    root_name = os.path.basename(req.root_dir) if req.root_dir else "project"
    selected_paths_set = set(req.selected_paths)

    try:
        payload = RustCoreService.build_payload(
            root_name,
            req.root_node,
            files_payload,
            selected_paths_set,
            options
        )
        tokens = RustCoreService.count_tokens(payload)
        size_kb = round(len(payload.encode("utf-8")) / 1024, 1)

        return PayloadResponse(
            payload=payload,
            token_count=tokens,
            files_count=len(files_payload),
            size_kb=size_kb
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка генерации контекста: {str(e)}")


@api_router.post("/payload/standalone-tree", response_model=StandaloneTreeResponse)
async def get_standalone_tree(req: StandaloneTreeRequest):
    try:
        tree = RustCoreService.generate_standalone_tree(
            req.root_name,
            req.root_node,
            set(req.selected_paths),
            req.xml_format
        )
        return StandaloneTreeResponse(tree_text=tree)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка генерации ASCII-дерева: {str(e)}")


@api_router.post("/payload/tokens", response_model=TokenCountResponse)
async def count_tokens_endpoint(req: TokenCountRequest):
    return TokenCountResponse(token_count=RustCoreService.count_tokens(req.text))


@api_router.post("/git/status", response_model=GitStatusResponse)
async def git_status_endpoint(req: GitStatusRequest):
    success, msg, files = GitService.get_modified_files(req.root_dir)
    return GitStatusResponse(success=success, message=msg, modified_files=files)


@api_router.post("/git/diff", response_model=GitDiffResponse)
async def git_diff_endpoint(req: GitDiffRequest):
    success, diff_text = GitService.get_git_diff(req.root_dir, req.context_lines)
    msg = "Успешно" if success else diff_text
    return GitDiffResponse(success=success, message=msg, diff_text=diff_text if success else "")


@api_router.post("/dependencies", response_model=DependenciesResponse)
async def trace_dependencies_endpoint(req: DependenciesRequest):
    content = req.content or ""
    if not content and req.root_dir and req.target_rel_path:
        full_path = os.path.join(req.root_dir, req.target_rel_path)
        if os.path.isfile(full_path):
            try:
                with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
            except Exception:
                content = ""

    deps = RustCoreService.trace_dependencies(req.root_dir, req.target_rel_path, content)
    return DependenciesResponse(dependencies=deps)


@api_router.get("/settings")
async def get_settings():
    return config_manager.settings


@api_router.post("/settings")
async def update_settings(settings_data: Dict[str, Any]):
    config_manager.save_settings(settings_data)
    return {"status": "success", "settings": config_manager.settings}


@api_router.get("/prompts")
async def get_prompts():
    return config_manager.prompts


@api_router.post("/prompts")
async def update_prompt(preset: PromptPreset):
    res = config_manager.update_prompt(preset.key, preset.title, preset.prompt)
    return {"status": "success", "prompt": res}


@api_router.delete("/prompts/{key}")
async def delete_prompt(key: str):
    success = config_manager.delete_prompt(key)
    return {"status": "success" if success else "failed"}


@api_router.get("/rules")
async def get_rules():
    return config_manager.rules


@api_router.post("/rules/custom")
async def add_custom_rule(rule: CustomRuleRequest):
    res = config_manager.add_custom_rule(rule.category, rule.title, rule.description, rule.rule_text)
    return {"status": "success", "rule": res}


@api_router.post("/rules/compile", response_model=CompilePromptResponse)
async def compile_rules(req: CompilePromptRequest):
    compiled = config_manager.compile_prompt(req.selected_rules)
    return CompilePromptResponse(compiled_prompt=compiled)


@api_router.post("/save-file", response_model=SaveFileResponse)
async def save_file_endpoint(req: SaveFileRequest):
    try:
        target_dir = os.path.dirname(req.file_path)
        if target_dir:
            os.makedirs(target_dir, exist_ok=True)
        with open(req.file_path, "w", encoding="utf-8") as f:
            f.write(req.content)
        return SaveFileResponse(success=True, message=f"Файл сохранен: {req.file_path}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка записи файла: {str(e)}")


@api_router.get("/watch/events")
async def watch_events_stream():
    loop = asyncio.get_running_loop()
    watcher_service.set_event_loop(loop)
    queue = watcher_service.register_listener()

    async def event_generator():
        try:
            while True:
                data = await queue.get()
                yield {
                    "event": "file_change",
                    "data": json.dumps(data)
                }
        except asyncio.CancelledError:
            watcher_service.unregister_listener(queue)

    return EventSourceResponse(event_generator())