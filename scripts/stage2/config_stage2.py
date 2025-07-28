# config_stage2.py
from pathlib import Path
from utils.logger import setup_logger


PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
STAGE1_FLAT_FILE = PROJECT_ROOT / "outputs/stage1/pain_points_stage1.jsonl"
STAGE2_INPUT_DIR = PROJECT_ROOT / "outputs/stage2/pain_points_by_course"
STAGE2_OUTPUT_DIR = PROJECT_ROOT / "outputs/stage2/clusters_by_course"
STAGE2_LOG_FILE = PROJECT_ROOT / "logs/stage2.log"

STAGE2_INPUT_DIR.mkdir(parents=True, exist_ok=True)
STAGE2_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ALERT_THRESHOLD = 2
FULL_BATCH_TOKEN_LIMIT = 16000  # adjust based on model limits
FALLBACK_CHUNK_SIZE = 5
MAX_RETRIES = 4
RETRY_SLEEP_SECONDS = 2
MODEL_NAME = "gpt-4o-mini"

logger = setup_logger("stage2", filename="stage2.log", to_console=True)

# Model config
MODEL_NAME = "gpt-4o-mini"
MAX_RETRIES = 4
RETRY_SLEEP_SECONDS = 2
