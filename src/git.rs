use std::collections::HashSet;
use std::process::Command;

#[cfg(target_os = "windows")]
use std::os::windows::process::CommandExt;

#[cfg(target_os = "windows")]
const CREATE_NO_WINDOW: u32 = 0x08000000;

pub struct GitService;

impl GitService {
    fn create_git_command() -> Command {
        let mut cmd = Command::new("git");
        #[cfg(target_os = "windows")]
        cmd.creation_flags(CREATE_NO_WINDOW);
        cmd
    }

    pub fn get_modified_files(root_dir: &str) -> (bool, String, Vec<String>) {
        let output = match Self::create_git_command()
            .args(["status", "--porcelain"])
            .current_dir(root_dir)
            .output()
        {
            Ok(o) => o,
            Err(e) => return (false, format!("Git error: {}", e), vec![]),
        };

        if !output.status.success() {
            return (false, "Папка не является Git-репозиторием".to_string(), vec![]);
        }

        let stdout = String::from_utf8_lossy(&output.stdout);
        let mut modified = HashSet::new();

        for line in stdout.lines() {
            if line.len() > 3 {
                let mut path = line[3..].trim();
                if let Some(pos) = path.find(" -> ") {
                    path = &path[pos + 4..];
                }
                let clean = path.trim_matches(|c| c == '"' || c == '\'').replace('\\', "/");
                modified.insert(clean);
            }
        }

        let mut sorted: Vec<String> = modified.into_iter().collect();
        sorted.sort();

        let count = sorted.len();
        (true, format!("Найдено {} измененных файлов", count), sorted)
    }

    pub fn get_git_diff(root_dir: &str, context_lines: usize) -> (bool, String) {
        let output = match Self::create_git_command()
            .args(["diff", &format!("-U{}", context_lines)])
            .current_dir(root_dir)
            .output()
        {
            Ok(o) => o,
            Err(e) => return (false, format!("Git error: {}", e)),
        };

        if !output.status.success() {
            return (false, "Ошибка вызова git diff".to_string());
        }

        let diff = String::from_utf8_lossy(&output.stdout).trim().to_string();
        if diff.is_empty() {
            (false, "Нет изменений для построения Git Diff".to_string())
        } else {
            (true, diff)
        }
    }
}