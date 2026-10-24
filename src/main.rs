#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod config;
mod git;
mod server;

use config::ConfigManager;
use server::{create_router, AppState};
use std::sync::Arc;
use tao::{
    dpi::LogicalSize,
    event::{Event, WindowEvent},
    event_loop::{ControlFlow, EventLoop},
    window::WindowBuilder,
};
use wry::{WebContext, WebViewBuilder};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let config = Arc::new(ConfigManager::new());
    let state = AppState { config };
    let app = create_router(state);

    let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await?;
    let port = listener.local_addr()?.port();

    tokio::spawn(async move {
        let _ = axum::serve(listener, app).await;
    });

    let target_url = format!("http://127.0.0.1:{}", port);

    let event_loop = EventLoop::new();
    let window = WindowBuilder::new()
        .with_title("CodeContext")
        .with_inner_size(LogicalSize::new(1400.0, 850.0))
        .with_min_inner_size(LogicalSize::new(1000.0, 650.0))
        .build(&event_loop)?;

    let data_dir = dirs::data_local_dir()
        .map(|p| p.join("CodeContext").join("webview"))
        .unwrap_or_else(|| std::env::temp_dir().join("codecontext_webview"));
    let _ = std::fs::create_dir_all(&data_dir);

    let mut web_context = WebContext::new(Some(data_dir));

    let builder = WebViewBuilder::with_web_context(&mut web_context)
        .with_url(&target_url)
        .with_devtools(true);

    #[cfg(any(target_os = "windows", target_os = "macos"))]
    let _webview = builder.build(&window)?;

    #[cfg(target_os = "linux")]
    let _webview = {
        use tao::platform::unix::WindowExtUnix;
        use wry::WebViewBuilderExtUnix;
        let vbox = window.default_vbox().ok_or("Failed to get default vbox")?;
        builder.build_gtk(vbox)?
    };

    event_loop.run(move |event, _, control_flow| {
        *control_flow = ControlFlow::Wait;

        if let Event::WindowEvent {
            event: WindowEvent::CloseRequested,
            ..
        } = event
        {
            *control_flow = ControlFlow::Exit;
        }
    });
}