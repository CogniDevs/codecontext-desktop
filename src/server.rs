use axum::{
    extract::{Path as AxumPath, Query, State},
    http::{header, StatusCode, Uri},
    response::IntoResponse,
    routing::{delete, get, post},
    Json, Router,
};
use codecontext_core::models::{FileNode, ScanOptions, TransformOptions};
use codecontext_core::scanner;
use codecontext_core::services::{self, FileInput};
use rust_embed::RustEmbed;
use serde::Deserialize;
use serde_json::{json, Value};
use std::collections::{HashMap, HashSet};
use std::fs;
use std::path::Path;
use std::sync::Arc;
use tower_http::cors::CorsLayer;

use crate::config::ConfigManager;
use crate::git::GitService;

#[derive(RustEmbed)]
#[folder = "dist_ui/"]
struct EmbeddedUI;

#[derive(Clone)]
pub struct AppState {
    pub config: Arc<ConfigManager>,
}

pub fn create_router(state: AppState) -> Router {
    let api = Router::new()
        .route("/status", get(get_status))
        .route("/select-folder", post(select_folder))
        .route("/select-save-file", post(select_save_file))
        .route("/gitignore", get(get_gitignore))
        .route("/scan", post(scan_directory))
        .route("/payload", post(build_payload))
        .route("/payload/standalone-tree", post(standalone_tree))
        .route("/payload/tokens", post(count_tokens))
        .route("/git/status", post(git_status))
        .route("/git/diff", post(git_diff))
        .route("/dependencies", post(trace_dependencies))
        .route("/settings", get(get_settings).post(save_settings))
        .route("/prompts", get(get_prompts).post(update_prompt))
        .route("/prompts/:key", delete(delete_prompt))
        .route("/rules", get(get_rules))
        .route("/rules/custom", post(add_custom_rule))
        .route("/rules/compile", post(compile_rules))
        .route("/save-file", post(save_file))
        .with_state(state);

    Router::new()
        .nest("/api", api)
        .fallback(embedded_static_handler)
        .layer(CorsLayer::permissive())
}

async fn embedded_static_handler(uri: Uri) -> impl IntoResponse {
    let mut path = uri.path().trim_start_matches('/').to_string();

    if let Some(stripped) = path.strip_prefix("codecontext-web/") {
        path = stripped.to_string();
    }

    if path.is_empty() {
        path = "index.html".to_string();
    }

    match EmbeddedUI::get(&path) {
        Some(content) => {
            let mime = mime_guess::from_path(&path).first_or_octet_stream();

            if path == "index.html" {
                if let Ok(html_str) = std::str::from_utf8(content.data.as_ref()) {
                    let patched = html_str
                        .replace("<base href=\"/codecontext-web/\">", "<base href=\"/\">")
                        .replace("<base href=\"/codecontext-web\">", "<base href=\"/\">");
                    return ([(header::CONTENT_TYPE, "text/html; charset=utf-8")], patched.into_bytes()).into_response();
                }
            }

            ([(header::CONTENT_TYPE, mime.as_ref())], content.data).into_response()
        }
        None => {
            if path.contains('.') && !path.ends_with(".html") {
                return (StatusCode::NOT_FOUND, "404 Not Found").into_response();
            }

            match EmbeddedUI::get("index.html") {
                Some(content) => {
                    if let Ok(html_str) = std::str::from_utf8(content.data.as_ref()) {
                        let patched = html_str
                            .replace("<base href=\"/codecontext-web/\">", "<base href=\"/\">")
                            .replace("<base href=\"/codecontext-web\">", "<base href=\"/\">");
                        ([(header::CONTENT_TYPE, "text/html; charset=utf-8")], patched.into_bytes()).into_response()
                    } else {
                        ([(header::CONTENT_TYPE, "text/html; charset=utf-8")], content.data).into_response()
                    }
                }
                None => (StatusCode::NOT_FOUND, "404 Not Found").into_response(),
            }
        }
    }
}

async fn get_status() -> Json<Value> {
    Json(json!({
        "status": "online",
        "desktop_bridge": true,
        "rust_engine_available": true,
        "current_version": env!("CARGO_PKG_VERSION"),
        "system_platform": std::env::consts::OS
    }))
}

async fn select_folder() -> Json<Value> {
    let folder = rfd::FileDialog::new().pick_folder();
    if let Some(path) = folder {
        Json(json!({ "success": true, "path": path.to_string_lossy().to_string() }))
    } else {
        Json(json!({ "success": false, "path": "" }))
    }
}

#[derive(Deserialize)]
struct SaveDialogReq {
    default_filename: Option<String>,
}

async fn select_save_file(Json(req): Json<Option<SaveDialogReq>>) -> Json<Value> {
    let mut dialog = rfd::FileDialog::new();
    if let Some(ref r) = req {
        if let Some(ref name) = r.default_filename {
            dialog = dialog.set_file_name(name);
        }
    }
    if let Some(path) = dialog.save_file() {
        Json(json!({ "success": true, "path": path.to_string_lossy().to_string() }))
    } else {
        Json(json!({ "success": false, "path": "" }))
    }
}

#[derive(Deserialize)]
struct GitignoreQuery {
    root_dir: String,
}

async fn get_gitignore(Query(q): Query<GitignoreQuery>) -> Json<Value> {
    let gitignore_path = Path::new(&q.root_dir).join(".gitignore");
    let mut rules = Vec::new();
    if let Ok(content) = fs::read_to_string(gitignore_path) {
        for line in content.lines() {
            let mut trimmed = line.trim();
            if trimmed.is_empty() || trimmed.starts_with('#') {
                continue;
            }
            if let Some(idx) = trimmed.find(" #") {
                trimmed = trimmed[..idx].trim();
            }
            if !trimmed.is_empty() {
                rules.push(trimmed.to_string());
            }
        }
    }
    Json(json!({ "rules": rules }))
}

#[derive(Deserialize)]
struct ScanReq {
    root_dir: String,
    options: Option<ScanOptions>,
}

async fn scan_directory(State(state): State<AppState>, Json(req): Json<ScanReq>) -> Result<Json<FileNode>, StatusCode> {
    let options = req.options.unwrap_or_else(|| {
        serde_json::from_value(state.config.get_settings()).unwrap_or_default()
    });

    scanner::scan_directory(&req.root_dir, &options)
        .map(Json)
        .ok_or(StatusCode::NOT_FOUND)
}

#[derive(Deserialize)]
struct PayloadReq {
    root_dir: String,
    root_node: Option<FileNode>,
    selected_paths: Vec<String>,
    options: TransformOptions,
    custom_files: Option<Vec<CustomFile>>,
}

#[derive(Deserialize)]
struct CustomFile {
    rel_path: String,
    content: String,
}

async fn build_payload(State(state): State<AppState>, Json(mut req): Json<PayloadReq>) -> Json<Value> {
    let mut files_payload: Vec<FileInput> = Vec::new();

    if let Some(cf) = req.custom_files {
        for item in cf {
            files_payload.push(FileInput { rel_path: item.rel_path, content: item.content });
        }
    } else if !req.options.git_diff_mode && !req.root_dir.is_empty() {
        for rel in &req.selected_paths {
            let full = Path::new(&req.root_dir).join(rel);
            let content = fs::read_to_string(&full).unwrap_or_else(|e| format!("[Ошибка чтения: {}]", e));
            files_payload.push(FileInput { rel_path: rel.clone(), content });
        }
    }

    if req.options.git_diff_mode && !req.root_dir.is_empty() {
        let (ok, diff) = GitService::get_git_diff(&req.root_dir, req.options.git_diff_context_lines);
        if ok {
            req.options.git_diff_text = Some(diff);
        }
    }

    req.options.comment_rules_json = serde_json::to_string(&state.config.comment_rules).ok();

    let root_name = Path::new(&req.root_dir)
        .file_name()
        .map(|n| n.to_string_lossy().to_string())
        .unwrap_or_else(|| "project".to_string());

    let selected_set: HashSet<String> = req.selected_paths.into_iter().collect();

    let payload = services::build_payload(
        &root_name,
        req.root_node.as_ref(),
        &files_payload,
        &selected_set,
        &req.options,
    );

    let tokens = codecontext_core::tokenizer::count_tokens(&payload);
    let size_kb = ((payload.as_bytes().len() as f64 / 1024.0) * 10.0).round() / 10.0;

    Json(json!({
        "payload": payload,
        "token_count": tokens,
        "files_count": files_payload.len(),
        "size_kb": size_kb
    }))
}

#[derive(Deserialize)]
struct StandaloneTreeReq {
    root_name: String,
    root_node: Option<FileNode>,
    selected_paths: Vec<String>,
    xml_format: bool,
}

async fn standalone_tree(Json(req): Json<StandaloneTreeReq>) -> Json<Value> {
    let selected_set: HashSet<String> = req.selected_paths.into_iter().collect();
    let tree = services::payload_service::generate_standalone_tree_payload(
        &req.root_name,
        req.root_node.as_ref(),
        &selected_set,
        req.xml_format,
    );
    Json(json!({ "tree_text": tree }))
}

#[derive(Deserialize)]
struct TokenReq {
    text: String,
}

async fn count_tokens(Json(req): Json<TokenReq>) -> Json<Value> {
    let count = codecontext_core::tokenizer::count_tokens(&req.text);
    Json(json!({ "token_count": count }))
}

#[derive(Deserialize)]
struct GitReq {
    root_dir: String,
}

async fn git_status(Json(req): Json<GitReq>) -> Json<Value> {
    let (success, message, files) = GitService::get_modified_files(&req.root_dir);
    Json(json!({ "success": success, "message": message, "modified_files": files }))
}

#[derive(Deserialize)]
struct GitDiffReq {
    root_dir: String,
    context_lines: usize,
}

async fn git_diff(Json(req): Json<GitDiffReq>) -> Json<Value> {
    let (success, diff_text) = GitService::get_git_diff(&req.root_dir, req.context_lines);
    Json(json!({ "success": success, "diff_text": if success { &diff_text } else { "" } }))
}

#[derive(Deserialize)]
struct DepsReq {
    root_dir: String,
    target_rel_path: String,
    content: Option<String>,
}

async fn trace_dependencies(Json(req): Json<DepsReq>) -> Json<Value> {
    let content = if let Some(c) = req.content {
        c
    } else {
        let full = Path::new(&req.root_dir).join(&req.target_rel_path);
        fs::read_to_string(full).unwrap_or_default()
    };
    let deps = services::trace_dependencies(&req.root_dir, &req.target_rel_path, &content);
    let deps_list: Vec<String> = deps.into_iter().collect();
    Json(json!({ "dependencies": deps_list }))
}

async fn get_settings(State(state): State<AppState>) -> Json<Value> {
    Json(state.config.get_settings())
}

async fn save_settings(State(state): State<AppState>, Json(val): Json<Value>) -> Json<Value> {
    state.config.save_settings(val.clone());
    Json(json!({ "status": "success", "settings": val }))
}

async fn get_prompts(State(state): State<AppState>) -> Json<Value> {
    Json(state.config.get_prompts())
}

async fn update_prompt(State(state): State<AppState>, Json(val): Json<Value>) -> Json<Value> {
    let mut prompts = state.config.get_prompts();
    if let (Some(key), Some(map)) = (val.get("key").and_then(|k| k.as_str()), prompts.as_object_mut()) {
        map.insert(key.to_string(), val.clone());
        state.config.save_prompts(prompts);
    }
    Json(json!({ "status": "success", "prompt": val }))
}

async fn delete_prompt(State(state): State<AppState>, AxumPath(key): AxumPath<String>) -> Json<Value> {
    let mut prompts = state.config.get_prompts();
    if let Some(map) = prompts.as_object_mut() {
        map.remove(&key);
        state.config.save_prompts(prompts);
    }
    Json(json!({ "status": "success" }))
}

async fn get_rules(State(state): State<AppState>) -> Json<Value> {
    Json(state.config.get_rules())
}

async fn add_custom_rule(State(state): State<AppState>, Json(val): Json<Value>) -> Json<Value> {
    let mut rules = state.config.get_rules();
    let category = val.get("category").and_then(|c| c.as_str()).unwrap_or("general");
    if let Some(map) = rules.as_object_mut() {
        let entry = map.entry(category).or_insert_with(|| json!([]));
        if let Some(arr) = entry.as_array_mut() {
            arr.push(val.clone());
        }
        state.config.save_rules(rules);
    }
    Json(json!({ "status": "success", "rule": val }))
}

#[derive(Deserialize)]
struct CompileRulesReq {
    selected_rules: HashMap<String, Vec<String>>,
}

async fn compile_rules(Json(req): Json<CompileRulesReq>) -> Json<Value> {
    let categories = [
        ("system_role", "expert_role"),
        ("interaction_protocol", "interaction_protocol"),
        ("quality_standards", "code_generation_standards"),
        ("version_alignment", "technology_alignment"),
    ];

    let mut lines = Vec::new();
    for (json_key, xml_tag) in categories {
        if let Some(rules) = req.selected_rules.get(json_key) {
            if !rules.is_empty() {
                lines.push(format!("<{}>", xml_tag));
                for r in rules {
                    lines.push(format!("  - {}", r));
                }
                lines.push(format!("</{}>\n", xml_tag));
            }
        }
    }
    Json(json!({ "compiled_prompt": lines.join("\n").trim() }))
}

#[derive(Deserialize)]
struct SaveFileReq {
    file_path: String,
    content: String,
}

async fn save_file(Json(req): Json<SaveFileReq>) -> Json<Value> {
    if let Some(parent) = Path::new(&req.file_path).parent() {
        let _ = fs::create_dir_all(parent);
    }
    match fs::write(&req.file_path, req.content) {
        Ok(_) => Json(json!({ "success": true, "message": "Файл успешно сохранен" })),
        Err(e) => Json(json!({ "success": false, "message": format!("Ошибка записи: {}", e) })),
    }
}