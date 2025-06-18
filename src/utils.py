import os
import sys
import logging
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# Add the project root directory to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.config import LOG_FORMAT, LOG_FILE, SOURCE_LANGUAGE_COL


def setup_logging() -> logging.Logger:
    """
    Configure a logger that writes INFO+ messages both to console and to a file.
    """
    logger = logging.getLogger("translation_processor")
    logger.setLevel(logging.INFO)

    # File handler
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(console_handler)

    return logger


def read_excel_safe(file_path: Path, logger: logging.Logger) -> Optional[pd.DataFrame]:
    """
    Attempt to read an Excel file into a DataFrame. 
    If it fails, log the error and return None.
    """
    try:
        # keep_default_na=False prevents strings like "None" or "N/A" from being
        # interpreted as missing values. This preserves those exact strings in
        # the DataFrame so they are written back out unchanged.
        return pd.read_excel(file_path, keep_default_na=False)
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {str(e)}")
        return None


def get_locale_code_from_filename(filename: str) -> str:
    """
    Given "de_DE.xlsx", return "de_de".
    (Lowercases and strips off the .xlsx extension.)
    """
    return Path(filename).stem.lower()
