import os
from pathlib import Path

# Project root directory
ROOT_DIR = Path(__file__).parent.parent

# Directory structure
INPUT_DIR = ROOT_DIR / "data" / "input"
MODULES_DIR = INPUT_DIR / "modules"  # Contains *_master.xlsx files
TRANSLATIONS_RAW_DIR = INPUT_DIR / "translations_raw"  # Contains language files
OUTPUT_DIR = ROOT_DIR / "data" / "output"
LOGS_DIR = ROOT_DIR / "logs"

# Create directories if they don't exist
for directory in [INPUT_DIR, MODULES_DIR, TRANSLATIONS_RAW_DIR, OUTPUT_DIR, LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Column configurations
SOURCE_LANGUAGE_COL = "English (US) [Primary]"  # Column name in module master files
TRANSLATION_SOURCE_COL = "en_US"  # Column name in translation files

# Logging configuration
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FILE = LOGS_DIR / "translation_processor.log" 