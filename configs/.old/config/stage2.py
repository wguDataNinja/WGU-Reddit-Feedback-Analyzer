from pathlib import Path
import datetime
from config import common

today = datetime.date.today().isoformat()

STAGE2_INPUT_DIR = common.OUTPUT_DIR / "runs" / today / "stage2_input"
STAGE2_OUTPUT_DIR = common.OUTPUT_DIR / "runs" / today / "stage2_output"

STAGE2_INPUT_DIR.mkdir(parents=True, exist_ok=True)
STAGE2_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

LOG_PATH = common.OUTPUT_DIR / "runs" / today / "logs" / "stage2.log"
ALERT_THRESHOLD = 2
FULL_BATCH_TOKEN_LIMIT = 16000