from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class FileNode(BaseModel):
    name: str
    full_path: str
    rel_path: str
    is_dir: bool
    size: int = 0
    children: List["FileNode"] = Field(default_factory=list)


FileNode.model_rebuild()


class ScanOptions(BaseModel):
    use_gitignore: bool = True
    ignore_binary: bool = True
    ignore_lockfiles: bool = True
    whitelist_extensions: List[str] = Field(default_factory=list)
    manual_excludes: List[str] = Field(default_factory=list)
    gitignore_disabled_rules: List[str] = Field(default_factory=list)
    binary_extensions: List[str] = Field(default_factory=list)
    lockfiles_excludes: List[str] = Field(default_factory=list)
    output_file_path: Optional[str] = None


class ScanRequest(BaseModel):
    root_dir: str
    options: Optional[ScanOptions] = None


class TransformOptions(BaseModel):
    strip_comments: bool = False
    compress_whitespace: bool = False
    sanitize_secrets: bool = False
    skeleton_mode: bool = False
    xml_format: bool = True
    always_send_full_tree: bool = False
    system_prompt: str = ""
    comment_rules_json: Optional[str] = None
    max_token_budget: Optional[int] = None
    git_diff_mode: bool = False
    git_diff_context_lines: int = 3
    git_diff_text: Optional[str] = None


class FilePayloadItem(BaseModel):
    rel_path: str
    content: str


class PayloadRequest(BaseModel):
    root_dir: str
    root_node: Optional[Dict[str, Any]] = None
    selected_paths: List[str] = Field(default_factory=list)
    options: TransformOptions = Field(default_factory=TransformOptions)
    custom_files: Optional[List[FilePayloadItem]] = None


class PayloadResponse(BaseModel):
    payload: str
    token_count: int
    files_count: int
    size_kb: float


class StandaloneTreeRequest(BaseModel):
    root_name: str
    root_node: Optional[Dict[str, Any]] = None
    selected_paths: List[str] = Field(default_factory=list)
    xml_format: bool = True


class StandaloneTreeResponse(BaseModel):
    tree_text: str


class GitStatusRequest(BaseModel):
    root_dir: str


class GitStatusResponse(BaseModel):
    success: bool
    message: str
    modified_files: List[str] = Field(default_factory=list)


class GitDiffRequest(BaseModel):
    root_dir: str
    context_lines: int = 3


class GitDiffResponse(BaseModel):
    success: bool
    message: str
    diff_text: str = ""


class DependenciesRequest(BaseModel):
    root_dir: str
    target_rel_path: str
    content: Optional[str] = None


class DependenciesResponse(BaseModel):
    dependencies: List[str] = Field(default_factory=list)


class TokenCountRequest(BaseModel):
    text: str


class TokenCountResponse(BaseModel):
    token_count: int


class PromptPreset(BaseModel):
    key: str
    title: str
    prompt: str
    custom: bool = False


class CustomRuleRequest(BaseModel):
    category: str
    title: str
    description: str
    rule_text: str


class CompilePromptRequest(BaseModel):
    selected_rules: Dict[str, List[str]] = Field(default_factory=dict)


class CompilePromptResponse(BaseModel):
    compiled_prompt: str


class SaveFileRequest(BaseModel):
    file_path: str
    content: str


class SaveFileResponse(BaseModel):
    success: bool
    message: str


class ServiceStatus(BaseModel):
    status: str
    desktop_bridge: bool
    rust_engine_available: bool
    current_version: str
    system_platform: str