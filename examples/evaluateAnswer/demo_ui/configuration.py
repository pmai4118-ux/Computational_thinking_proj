from pathlib import Path

from source.service.demoConfiguration import DemoConfiguration


DEFAULT_MODEL = DemoConfiguration.defaultModel
LOCAL_SETTINGS_PATH = Path(__file__).resolve().parents[3] / "secrets" / "demo-gemini.json"
selectedProvider = DemoConfiguration.selectedProvider
loadAntigravitySettings = DemoConfiguration.loadAntigravitySettings
loadDemoSettings = DemoConfiguration.loadDemoSettings
