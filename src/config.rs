use serde_json::Value;
use std::fs;
use std::path::PathBuf;

static DEFAULT_SETTINGS: &str = include_str!("../resources/default_settings.json");
static DEFAULT_PROMPTS: &str = include_str!("../resources/default_prompts.json");
static DEFAULT_RULES: &str = include_str!("../resources/default_rules.json");
static COMMENT_RULES: &str = include_str!("../resources/comment_rules.json");

pub struct ConfigManager {
    pub settings_path: PathBuf,
    pub prompts_path: PathBuf,
    pub rules_path: PathBuf,
    pub default_settings: Value,
    pub default_prompts: Value,
    pub default_rules: Value,
    pub comment_rules: Value,
}

impl ConfigManager {
    pub fn new() -> Self {
        let config_dir = dirs::config_dir()
            .map(|d| d.join("CodeContext"))
            .unwrap_or_else(|| PathBuf::from(".config"));
        let _ = fs::create_dir_all(&config_dir);

        let default_settings = serde_json::from_str(DEFAULT_SETTINGS).unwrap_or(Value::Null);
        let default_prompts = serde_json::from_str(DEFAULT_PROMPTS).unwrap_or(Value::Null);
        let default_rules = serde_json::from_str(DEFAULT_RULES).unwrap_or(Value::Null);
        let comment_rules = serde_json::from_str(COMMENT_RULES).unwrap_or(Value::Null);

        let settings_path = config_dir.join("settings.json");
        let prompts_path = config_dir.join("prompts.json");
        let rules_path = config_dir.join("rules.json");

        let manager = Self {
            settings_path,
            prompts_path,
            rules_path,
            default_settings,
            default_prompts,
            default_rules,
            comment_rules,
        };

        manager.ensure_files();
        manager
    }

    fn ensure_files(&self) {
        if !self.settings_path.exists() {
            let _ = fs::write(&self.settings_path, serde_json::to_string_pretty(&self.default_settings).unwrap_or_default());
        }
        if !self.prompts_path.exists() {
            let _ = fs::write(&self.prompts_path, serde_json::to_string_pretty(&self.default_prompts).unwrap_or_default());
        }
        if !self.rules_path.exists() {
            let _ = fs::write(&self.rules_path, serde_json::to_string_pretty(&self.default_rules).unwrap_or_default());
        }
    }

    pub fn get_settings(&self) -> Value {
        fs::read_to_string(&self.settings_path)
            .ok()
            .and_then(|s| serde_json::from_str(&s).ok())
            .unwrap_or_else(|| self.default_settings.clone())
    }

    pub fn save_settings(&self, val: Value) -> Value {
        let _ = fs::write(&self.settings_path, serde_json::to_string_pretty(&val).unwrap_or_default());
        val
    }

    pub fn get_prompts(&self) -> Value {
        fs::read_to_string(&self.prompts_path)
            .ok()
            .and_then(|s| serde_json::from_str(&s).ok())
            .unwrap_or_else(|| self.default_prompts.clone())
    }

    pub fn save_prompts(&self, val: Value) -> Value {
        let _ = fs::write(&self.prompts_path, serde_json::to_string_pretty(&val).unwrap_or_default());
        val
    }

    pub fn get_rules(&self) -> Value {
        fs::read_to_string(&self.rules_path)
            .ok()
            .and_then(|s| serde_json::from_str(&s).ok())
            .unwrap_or_else(|| self.default_rules.clone())
    }

    pub fn save_rules(&self, val: Value) -> Value {
        let _ = fs::write(&self.rules_path, serde_json::to_string_pretty(&val).unwrap_or_default());
        val
    }
}