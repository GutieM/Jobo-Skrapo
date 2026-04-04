# GutieM #4/2026

import re
from pathlib import Path

#global constraints -> stay as constants
MAX_FILE_SIZE_BYTES = 51_200 #50KB
MAX_TERM_LENGTH = 200

#section headers set to persist, supports sorting/scoring system
SECTION_HEADERS = {
    "[required]": "required",
    "[semi-helpful]" : "semi_helpful",
    "[concerning]": "concerning"    
}

def load_criteria(path: str) -> dict:
    """
    Load and validate a criteria file, returning structured scoring data.

    Args:
        path: Path to the criteria .txt file.

    Returns:
        dict with keys 'required', 'semi_helpful', 'concerning',
        each containing a list of validated regex term strings.

    Raises:
        TypeError: if path is not a string.
        FileNotFoundError: if the file does not exist.
        ValueError: if the file is too large, a term exceeds MAX_TERM_LENGTH,
            or a term is not a valid regex.
    """
    _validate_file(path)
    raw = Path(path).read_text(encoding="utf-8")
    sections = _parse_sections(raw)
    _validate_terms(sections)
    return sections

def _validate_file(path: str) -> None:
    ...

def _parse_sections():
    ...

def _validate_terms():
    ...