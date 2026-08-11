"""Analyzer module for the mini-project.

This module provides the `analyze` function which reads a parsed dictionary
from `parser.py` and computes statistics such as word count, unique words,
and other relevant metrics.
"""

from typing import Dict, Any


def analyze(parsed_data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze the parsed data and return statistics.

    Args:
        parsed_data: A dictionary containing parsed data from the input file.

    Returns:
        A dictionary containing computed statistics.
    """
    stats = {
        "word_count": 0,
        "unique_words": set(),
        "average_word_length": 0.0,
        "longest_word": "",
        "shortest_word": "",
    }

    # Assuming parsed_data contains a 'words' key with a list of words
    words = parsed_data.get("words", [])

    if not words:
        return stats

    stats["word_count"] = len(words)
    stats["unique_words"] = set(words)

    total_length = sum(len(word) for word in words)
    stats["average_word_length"] = total_length / len(words)

    stats["longest_word"] = max(words, key=len)
    stats["shortest_word"] = min(words, key=len)

    return stats
