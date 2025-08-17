"""internal-assistant."""

import logging
import os
from pathlib import Path

# Set to 'DEBUG' to have extensive logging turned on, even for libraries
# Can be overridden by PGPT_LOG_LEVEL environment variable
ROOT_LOG_LEVEL = os.environ.get("PGPT_LOG_LEVEL", "INFO")

PRETTY_LOG_FORMAT = (
    "%(asctime)s.%(msecs)03d [%(levelname)-8s] %(name)+25s - %(message)s"
)

# Create Logs directory if it doesn't exist
logs_dir = Path("Logs")
logs_dir.mkdir(exist_ok=True)

def get_next_session_number() -> int:
    """Find the next available session number by checking existing SessionLogN.log files."""
    session_files = list(logs_dir.glob("SessionLog*.log"))
    if not session_files:
        return 1
    
    # Extract numbers from existing session log files
    session_numbers = []
    for file_path in session_files:
        filename = file_path.stem  # Gets filename without extension
        if filename.startswith("SessionLog"):
            try:
                number = int(filename[10:])  # Extract number after "SessionLog"
                session_numbers.append(number)
            except ValueError:
                continue
    
    return max(session_numbers) + 1 if session_numbers else 1

# Configure session-based file handler
session_number = get_next_session_number()
session_log_file = logs_dir / f"SessionLog{session_number}.log"

file_handler = logging.FileHandler(
    session_log_file,
    mode="w",  # Create new session log file
    encoding="utf-8"
)

# Configure logging with both console and file handlers
logging.basicConfig(
    level=ROOT_LOG_LEVEL, 
    format=PRETTY_LOG_FORMAT, 
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(),  # Console handler
        file_handler  # File handler (overwrites each session)
    ]
)

logging.captureWarnings(True)

# Disable gradio analytics
# This is done this way because gradio does not solely rely on what values are
# passed to gr.Blocks(enable_analytics=...) but also on the environment
# variable GRADIO_ANALYTICS_ENABLED. `gradio.strings` actually reads this env
# directly, so to fully disable gradio analytics we need to set this env var.
os.environ["GRADIO_ANALYTICS_ENABLED"] = "False"

# Disable chromaDB telemetry
# It is already disabled, see PR#1144
# os.environ["ANONYMIZED_TELEMETRY"] = "False"

# adding tiktoken cache path within repo to be able to run in offline environment.
os.environ["TIKTOKEN_CACHE_DIR"] = "tiktoken_cache"
