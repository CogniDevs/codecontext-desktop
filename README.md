<p align="right">
  <b>English</b> | <a href="README.ru.md">Русский</a>
</p>

# CodeContext Desktop

Portable desktop application for **CodeContext** across Windows, macOS, and Linux. Provides native access to local filesystems, local Git CLI, and automated LLM-ready codebase packaging without browser sandbox limitations.

Packaged as a single standalone executable — external runtimes (Node.js, Python) are not required. The web UI is embedded directly into the binary.

👉 **[Download Releases](../../releases)**

---

## Desktop Features

- **Direct Filesystem Access**: Fast directory scanning without browser permission modals or upload ceilings.
- **Git Diff Mode (Delta Context)**: Generates minimal unified patches (`git diff -U<n>`) instead of full codebase dumps, reducing token consumption by up to 95-98%.
- **Git Status Synchronization**: Automatically detects and highlights modified, untracked, and staged files.
- **Native System Dialogs**: Seamless directory selection and export path pickers powered by `rfd`.
- **File Watcher**: Observes disk modifications and triggers incremental context preview updates.
- **Full Offline Autonomy**: Web UI and Rust core engine packaged together for air-gapped environments.

---

## Architecture

- **Windowing**: `tao` (cross-platform window creation).
- **GUI Engine**: `wry` (native webview: WebView2 on Windows, WebKitGTK on Linux, WKWebView on macOS).
- **Local Daemon**: `axum` + `tokio` (local HTTP API bound to loopback `127.0.0.1`).
- **Core Engine**: Direct dependency on `codecontext-core` (Tree-sitter AST, `cl100k_base` tiktoken, secret sanitizer, comment stripper).
- **Embedded UI**: Angular production build (`dist_ui/`) compiled into the binary via `rust-embed`.

---

## Requirements

### Runtime
- **Windows**: Windows 10/11 (WebView2 Runtime included by default).
- **macOS**: macOS 11 (Big Sur) or newer.
- **Linux**: Installed WebKitGTK and GTK-3 packages:
  - Ubuntu / Debian / Mint: `sudo apt install -y libwebkit2gtk-4.1-0 libgtk-3-0`
  - Fedora / RHEL: `sudo dnf install -y webkit2gtk4.1 gtk3`
  - Arch Linux / Manjaro: `sudo pacman -S webkit2gtk-4.1 gtk3`

### Build from Source
- **Rust**: `stable` (1.78+)
- Built web assets in `dist_ui/`
- Linux build dependencies:
  ```bash
  sudo apt-get update
  sudo apt-get install -y libwebkit2gtk-4.1-dev libgtk-3-dev libsoup-3.0-dev javascriptcoregtk-4.1-dev
  ```

---

## Build

```bash
cargo build --release
```

Binary is output to `target/release/codecontext-desktop`.
