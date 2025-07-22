# filename: utils/paths.py

from pathlib import Path

# Always resolves to the project root (WGU-Reddit/)
ROOT_DIR = Path(__file__).parent.parent.resolve()

# Input/output data folders
DATA_DIR = ROOT_DIR / "data"
OUTPUT_DIR = ROOT_DIR / "outputs"
DB_PATH = ROOT_DIR / "db" / "WGU-Reddit.db"

# OpenAI API config
OPENAI_MODULE_PATH = ROOT_DIR / "Ivy" / "OpenAI"
CONFIG_PATH = OPENAI_MODULE_PATH / "api_config.yaml"

# Convenience path joiner
def path(*parts):
    return ROOT_DIR.joinpath(*parts)