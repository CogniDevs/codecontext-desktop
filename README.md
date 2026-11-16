# CodeContext Desktop

<details open>
<summary><b>English</b></summary>

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
</details>

<details>
<summary><b>Русский</b></summary>

Портативное настольное приложение **CodeContext** для Windows, macOS и Linux. Предоставляет нативный доступ к файловой системе, локальному Git CLI и автоматическому формированию контекста для нейросетей без ограничений веб-браузера.

Поставляется в виде единого исполняемого файла (Single-file Portable) — рантаймы (Node.js, Python и др.) не требуются. Веб-интерфейс запечён прямо в бинарник.

👉 **[Скачать готовый бинарник (Releases)](../../releases)**

---

## Возможности Desktop-версии

- **Прямой доступ к файловой системе:** мгновенное сканирование любых директорий без ограничений браузерных API и диалогов подтверждения доступа к файлам.
- **Режим Git Diff (Дельта-контекст):** генерация сжатого патча реальных изменений репозитория (`git diff -U<n>`) вместо отправки всего кода — экономит до 95-98% токенов при ревью и доработках.
- **Синхронизация с Git Status:** автоматическое обнаружение и выделение только изменённых, новых или модифицированных файлов.
- **Системные диалоги:** нативный выбор папок проектов и путей сохранения через системный File Picker (`rfd`).
- **Авто-слежение (File Watcher):** отслеживание изменений на диске и автоматическое обновление превью контекста на лету.
- **Полная автономность:** веб-интерфейс и вычислительное ядро упакованы в один файл, интернет для работы не требуется.

---

## Архитектура

- **Оконная система:** `tao` (кроссплатформенное создание окон).
- **GUI-рендерер:** `wry` (нативный системный движок: WebView2 на Windows, WebKitGTK на Linux, WKWebView на macOS).
- **Локальный бэкенд:** `axum` + `tokio` (локальный HTTP API на случайном порту `127.0.0.1`).
- **Вычислительное ядро:** прямое подключение крейта `codecontext-core` (Tree-sitter, токенизация `tiktoken`, маскирование секретов, скелетонизация).
- **Вшивание ассетов:** Angular-бандл интерфейса (`dist_ui/`) запекается в бинарник через `rust-embed`.

---

## Системные требования

### Для запуска
- **Windows:** Windows 10/11 (компонент WebView2 Runtime, предустановлен в системе).
- **macOS:** macOS 11 (Big Sur) или новее.
- **Linux:** установленные системные пакеты WebKitGTK и GTK-3:
  - **Ubuntu / Debian / Mint:** `sudo apt install -y libwebkit2gtk-4.1-0 libgtk-3-0`
  - **Fedora / RHEL:** `sudo dnf install -y webkit2gtk4.1 gtk3`
  - **Arch Linux / Manjaro:** `sudo pacman -S webkit2gtk-4.1 gtk3`

### Для сборки из исходников
- **Rust:** `stable` (1.78+)
- Скомпилированный UI в папке `dist_ui/` (скачивается из релизов `codecontext-web` или собирается вручную).
- Зависимости для Linux:
  ```bash
  sudo apt-get update
  sudo apt-get install -y libwebkit2gtk-4.1-dev libgtk-3-dev libsoup-3.0-dev javascriptcoregtk-4.1-dev
  ```

---

## Сборка

Репозиторий `codecontext-core` должен находиться по относительному пути `../codecontext-core`.

1. **Подготовка интерфейса:**  
   Поместите собранные файлы веб-интерфейса в папку `dist_ui/` в корне проекта (внутри должен лежать `dist_ui/index.html`).

2. **Компиляция релиза:**
   ```bash
   cargo build --release
   ```

Готовый бинарник:
- **Windows:** `target/release/codecontext-desktop.exe`
- **Linux / macOS:** `target/release/codecontext-desktop`

На Windows бинарник собирается в оконной подсистеме без открытия фонового окна терминала.

---

## Конфигурация

Пользовательские настройки, пресеты промптов и правила хранятся в стандартных системных каталогах:
- **Windows:** `%APPDATA%\CodeContext\`
- **Linux:** `~/.config/CodeContext/`
- **macOS:** `~/Library/Application Support/CodeContext/`
</details>
