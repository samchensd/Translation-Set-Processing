import sys
from pathlib import Path
from typing import Dict, Tuple, List

import pandas as pd

# Add the parent directory to Python path so 'src' module can be found
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.config import (
    MODULES_DIR,
    TRANSLATIONS_RAW_DIR,
    OUTPUT_DIR,
    SOURCE_LANGUAGE_COL,
    TRANSLATION_SOURCE_COL,
)
from src.utils import (
    setup_logging,
    read_excel_safe,
    get_locale_code_from_filename,
)


class ModuleTranslationAugmentor:
    """
    For each module's English master (in MODULES_DIR), find where its rows appear
    inside a concatenated 'en_US' column in one of the language files (in TRANSLATIONS_RAW_DIR),
    compute start/end offsets accordingly, then for every language file slice those rows,
    append as new columns, and write out ModuleName_all_languages.xlsx to OUTPUT_DIR.
    """

    def __init__(self):
        self.logger = setup_logging()

        # Will hold each locale's full DataFrame of all modules concatenated:
        self.language_dfs: Dict[str, pd.DataFrame] = {}

        # Maps module_name -> the list of English strings in that module, in order:
        self.module_english_lists: Dict[str, List[str]] = {}

        # Maps module_name -> (start_row_index, end_row_index) in the combined sheets:
        self.offsets: Dict[str, Tuple[int, int]] = {}

        # Maps module_name -> its base English DataFrame
        self.module_bases: Dict[str, pd.DataFrame] = {}

        # Total number of rows across all modules (sum of lengths of each master)
        self.total_rows: int = 0

    def run(self) -> bool:
        """
        1) Load all module masters to record their English lists and total row count.
        2) Read one language file (first in alphabetical order) to compute offsets by matching
           each module's English list inside that file's 'en_US' column.
        3) Load every language file and slice each module's range, appending translation columns.
        4) Write out per-module merged workbooks.
        """
        if not self._load_module_masters():
            return False

        if not self._compute_offsets_from_first_language():
            return False

        self._load_all_language_files_and_write_modules()
        return True

    def _load_module_masters(self) -> bool:
        """
        Scan MODULES_DIR for Excel files. For each:
          - Read it into self.module_bases[module_name].
          - Record its English string list under module_english_lists[module_name].
          - Accumulate total_rows.
        Returns False if any file fails to load or lacks SOURCE_LANGUAGE_COL.
        """
        master_files = list(MODULES_DIR.glob("*.xlsx"))
        if not master_files:
            self.logger.error("No module files found in MODULES_DIR.")
            return False

        master_files.sort(key=lambda p: p.stem.lower())
        cumulative = 0

        for file_path in master_files:
            module_name = file_path.stem
            df = read_excel_safe(file_path, self.logger)
            if df is None:
                self.logger.error(f"Cannot load module '{module_name}'. Aborting.")
                return False

            if SOURCE_LANGUAGE_COL not in df.columns:
                self.logger.error(
                    f"Module '{module_name}' missing column '{SOURCE_LANGUAGE_COL}'."
                )
                return False

            # Save base DataFrame
            self.module_bases[module_name] = df.copy()

            # Extract English list for offset matching
            english_list = df[SOURCE_LANGUAGE_COL].astype(str).tolist()
            self.module_english_lists[module_name] = english_list

            row_count = len(english_list)
            cumulative += row_count
            self.logger.info(f"Loaded module '{module_name}' ({row_count} rows)")

        self.total_rows = cumulative
        self.logger.info(f"Total rows across all modules: {self.total_rows}")
        return True

    
    def _compute_offsets_from_first_language(self) -> bool:
        lang_files = list(TRANSLATIONS_RAW_DIR.glob("*.xlsx"))
        if not lang_files:
            self.logger.error("No language files found in TRANSLATIONS_RAW_DIR.")
            return False

        lang_files.sort(key=lambda p: p.stem.lower())
        first_lang = lang_files[0]
        self.logger.info(f"Using '{first_lang.name}' to compute offsets")

        df_lang = read_excel_safe(first_lang, self.logger)
        if df_lang is None:
            self.logger.error(f"Failed to read '{first_lang.name}' for offset computation.")
            return False

        if TRANSLATION_SOURCE_COL not in df_lang.columns:
            self.logger.error(
                f"'{first_lang.name}' missing required column '{TRANSLATION_SOURCE_COL}'."
            )
            return False

        concatenated_english = df_lang[TRANSLATION_SOURCE_COL].astype(str).tolist()
        if len(concatenated_english) != self.total_rows:
            self.logger.error(
                f"'{first_lang.name}' has {len(concatenated_english)} rows but expected {self.total_rows}."
            )
            return False

        # Instead of “starting at 0 for the first module, >end for subsequent,”
        # we simply scan from index 0 every time:
        for module_name, eng_list in self.module_english_lists.items():
            match_index = self._find_subsequence_index(concatenated_english, eng_list, start=0)
            if match_index < 0:
                self.logger.error(
                    f"Could not match module '{module_name}' English block in '{first_lang.name}'."
                )
                return False

            start_idx = match_index
            end_idx = start_idx + len(eng_list)
            self.offsets[module_name] = (start_idx, end_idx)
            self.logger.info(
                f"Computed offsets for '{module_name}': ({start_idx}, {end_idx})"
            )

        return True

    @staticmethod
    def _find_subsequence_index(haystack: List[str], needle: List[str], start: int = 0) -> int:
        """
        Return the first index >= start where haystack[i:i+len(needle)] == needle.
        If not found, return -1.
        """
        n, m = len(haystack), len(needle)
        if m == 0 or n < m:
            return -1

        # Naively scan
        for i in range(start, n - m + 1):
            if haystack[i : i + m] == needle:
                return i
        return -1

    def _load_all_language_files_and_write_modules(self) -> None:
        """
        For each "*.xlsx" in TRANSLATIONS_RAW_DIR:
          1) Read the entire sheet into df_lang.
          2) Verify it has total_rows rows.
          3) Identify the single translated-text column (everything except TRANSLATION_SOURCE_COL).
          4) Rename that column to the locale code (e.g. 'de_de').
          5) For each module, slice df_lang.iloc[start:end], append slice[locale].values to df_merged.
          6) Write out each module's merged DataFrame once all locales are appended.
        """
        lang_files = list(TRANSLATIONS_RAW_DIR.glob("*.xlsx"))
        if not lang_files:
            self.logger.error("No language files found in TRANSLATIONS_RAW_DIR.")
            return

        lang_files.sort(key=lambda p: p.stem.lower())

        # Prepare a dict to hold merged DataFrames, one per module
        merged_dfs: Dict[str, pd.DataFrame] = {
            module_name: base_df.copy()
            for module_name, base_df in self.module_bases.items()
        }

        for file_path in lang_files:
            locale = get_locale_code_from_filename(file_path.name)  # e.g. "de_de"
            self.logger.info(f"\nProcessing language file: {file_path.name} → locale: {locale}")

            df_lang = read_excel_safe(file_path, self.logger)
            if df_lang is None:
                self.logger.error(f"Skipping locale '{locale}' because it failed to read.")
                continue

            if TRANSLATION_SOURCE_COL not in df_lang.columns:
                self.logger.error(
                    f"Locale file {file_path.name} missing required column '{TRANSLATION_SOURCE_COL}'. Skipping."
                )
                continue

            cols = df_lang.columns.tolist()
            trans_cols = [c for c in cols if c not in (TRANSLATION_SOURCE_COL,)]
            if len(trans_cols) != 1:
                self.logger.error(
                    f"Locale file {file_path.name} must have exactly one translated-text column. "
                    f"Found: {trans_cols}. Skipping."
                )
                continue

            translated_col = trans_cols[0]
            actual_rows = df_lang.shape[0]
            if actual_rows != self.total_rows:
                self.logger.error(
                    f"Locale file {file_path.name} has {actual_rows} rows, "
                    f"but expected {self.total_rows}. Skipping."
                )
                continue

            # Rename the translated-text column to the locale code
            df_lang[locale] = df_lang[translated_col]

            # For each module, slice and append
            for module_name, (start_idx, end_idx) in self.offsets.items():
                df_merged = merged_dfs[module_name]
                slice_lang = df_lang.iloc[start_idx:end_idx]

                # Sanity-check English alignment
                eng_base = self.module_bases[module_name][SOURCE_LANGUAGE_COL].astype(str).tolist()
                eng_slice = slice_lang[TRANSLATION_SOURCE_COL].astype(str).tolist()
                if eng_base != eng_slice:
                    self.logger.warning(
                        f"Mismatch in English text for module '{module_name}', locale '{locale}'.\n"
                        f"First few base rows: {eng_base[:3]}\n"
                        f"First few slice rows: {eng_slice[:3]}"
                    )

                # Assign by positional values
                df_merged[locale] = slice_lang[locale].values
                self.logger.info(
                    f"Appended locale '{locale}' to module '{module_name}' "
                    f"({end_idx - start_idx} rows)"
                )

        # Write out each merged module DataFrame
        for module_name, df_final in merged_dfs.items():
            out_path = OUTPUT_DIR / f"{module_name}_all_languages.xlsx"
            try:
                df_final.to_excel(out_path, index=False)
                self.logger.info(f"Successfully wrote merged file: {out_path}")
            except Exception as e:
                self.logger.error(f"Failed to save module '{module_name}' → {e}")


def main():
    augmentor = ModuleTranslationAugmentor()
    success = augmentor.run()
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
