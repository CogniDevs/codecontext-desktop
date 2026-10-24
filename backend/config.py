import os
import sys
import json
import time
from typing import Dict, Any, List, Optional


def get_resource_path(relative_path: str) -> str:
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, relative_path)


class ConfigManager:
    def __init__(self):
        if os.name == 'nt':
            self.config_dir = os.path.join(os.getenv('APPDATA', ''), 'CodeContext')
        else:
            self.config_dir = os.path.expanduser('~/.config/CodeContext')

        self.settings_path = os.path.join(self.config_dir, 'settings.json')
        self.prompts_path = os.path.join(self.config_dir, 'prompts.json')
        self.rules_path = os.path.join(self.config_dir, 'rules.json')

        os.makedirs(self.config_dir, exist_ok=True)

        self.default_settings = self.load_json_resource("resources/default_settings.json")
        self.default_prompts = self.load_json_resource("resources/default_prompts.json")
        self.default_rules = self.load_json_resource("resources/default_rules.json")
        self.comment_rules = self.load_json_resource("resources/comment_rules.json")

        self.settings = self.load_settings()
        self.prompts = self.load_prompts()
        self.rules = self.load_rules()

    def load_json_resource(self, relative_path: str) -> Dict[str, Any]:
        path = get_resource_path(relative_path)
        if not os.path.exists(path):
            return {}
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}

    def load_settings(self) -> Dict[str, Any]:
        if not os.path.exists(self.settings_path):
            self.save_settings(self.default_settings)
            return dict(self.default_settings)
        try:
            with open(self.settings_path, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
            modified = False
            for key, val in self.default_settings.items():
                if key not in loaded:
                    loaded[key] = val
                    modified = True
            if modified:
                self.save_settings(loaded)
            return loaded
        except Exception:
            self.save_settings(self.default_settings)
            return dict(self.default_settings)

    def save_settings(self, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if data is not None:
            self.settings = data
        try:
            with open(self.settings_path, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
        return self.settings

    def get_setting(self, key: str, default: Any = None) -> Any:
        return self.settings.get(key, default)

    def set_setting(self, key: str, value: Any) -> None:
        self.settings[key] = value
        self.save_settings()

    def load_prompts(self) -> Dict[str, Any]:
        if not os.path.exists(self.prompts_path):
            self.save_prompts(self.default_prompts)
            return dict(self.default_prompts)
        try:
            with open(self.prompts_path, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
            modified = False
            for key, val in self.default_prompts.items():
                if key not in loaded:
                    loaded[key] = val
                    modified = True
            if modified:
                self.save_prompts(loaded)
            return loaded
        except Exception:
            self.save_prompts(self.default_prompts)
            return dict(self.default_prompts)

    def save_prompts(self, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if data is not None:
            self.prompts = data
        try:
            with open(self.prompts_path, 'w', encoding='utf-8') as f:
                json.dump(self.prompts, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
        return self.prompts

    def update_prompt(self, key: str, title: str, prompt_text: str) -> Dict[str, Any]:
        self.prompts[key] = {
            "title": title,
            "prompt": prompt_text,
            "custom": True
        }
        self.save_prompts()
        return self.prompts[key]

    def delete_prompt(self, key: str) -> bool:
        if key in self.prompts and self.prompts[key].get("custom", False):
            del self.prompts[key]
            self.save_prompts()
            return True
        return False

    def load_rules(self) -> Dict[str, Any]:
        if not os.path.exists(self.rules_path):
            self.save_rules(self.default_rules)
            return dict(self.default_rules)
        try:
            with open(self.rules_path, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
            modified = False
            for category, rules_list in self.default_rules.items():
                if category not in loaded:
                    loaded[category] = rules_list
                    modified = True
                else:
                    loaded_ids = {rule.get("id") for rule in loaded[category] if isinstance(rule, dict)}
                    for rule in rules_list:
                        if isinstance(rule, dict) and rule.get("id") not in loaded_ids:
                            loaded[category].append(rule)
                            modified = True
            if modified:
                self.save_rules(loaded)
            return loaded
        except Exception:
            self.save_rules(self.default_rules)
            return dict(self.default_rules)

    def save_rules(self, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if data is not None:
            self.rules = data
        try:
            with open(self.rules_path, 'w', encoding='utf-8') as f:
                json.dump(self.rules, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
        return self.rules

    def add_custom_rule(self, category: str, title: str, description: str, rule_text: str) -> Dict[str, Any]:
        if category not in self.rules:
            self.rules[category] = []
        new_rule = {
            "id": f"custom_rule_{int(time.time() * 1000)}",
            "title": title,
            "description": description,
            "rule_text": rule_text,
            "active": True
        }
        self.rules[category].append(new_rule)
        self.save_rules()
        return new_rule

    def compile_prompt(self, selected_rules_by_category: Dict[str, List[str]]) -> str:
        lines = []
        categories_mapping = {
            "system_role": "expert_role",
            "interaction_protocol": "interaction_protocol",
            "quality_standards": "code_generation_standards",
            "version_alignment": "technology_alignment"
        }
        for json_key, xml_tag in categories_mapping.items():
            rules_list = selected_rules_by_category.get(json_key, [])
            if rules_list:
                lines.append(f"<{xml_tag}>")
                for rule_text in rules_list:
                    lines.append(f"  - {rule_text}")
                lines.append(f"</{xml_tag}>\n")
        return "\n".join(lines).strip()


config_manager = ConfigManager()