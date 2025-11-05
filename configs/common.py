from pathlib import Path
import os

# Require explicit API key in environment. No fallback allowed.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# Project root
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Shared directories
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_ROOT = os.getenv("PIPELINE_OUTPUT_ROOT", "outputs")
OUTPUT_DIR = PROJECT_ROOT / OUTPUT_ROOT

# Shared model defaults
MODEL_NAME = "gpt-4o-mini"
MAX_RETRIES = 4
RETRY_SLEEP_SECONDS = 2

# Logs directory
LOGS_DIR = OUTPUT_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

PIPELINE_LOG_PATH = LOGS_DIR / "pipeline.log"
STAGE1_LOG_PATH = LOGS_DIR / "stage1.log"
STAGE2_LOG_PATH = LOGS_DIR / "stage2.log"



# Reddit API credentials (override via env vars for security)
REDDIT_CREDENTIALS = {
    'client_id':     os.getenv('REDDIT_CLIENT_ID',     '2AdPjpG_iSQh0TWD6nKjEg'),
    'client_secret': os.getenv('REDDIT_CLIENT_SECRET', 'uMUTf6xmHSMmaL751WXAoJG0URjaDw'),
    'user_agent':    os.getenv('REDDIT_USER_AGENT',    'Subreddit Sentiment Analysis by u/BuddyOwensPVB'),
    'username':      os.getenv('REDDIT_USERNAME',      'BuddyOwensPVB'),
    'password':      os.getenv('REDDIT_PASSWORD',      'X7^x4RctF$*z'),
}


