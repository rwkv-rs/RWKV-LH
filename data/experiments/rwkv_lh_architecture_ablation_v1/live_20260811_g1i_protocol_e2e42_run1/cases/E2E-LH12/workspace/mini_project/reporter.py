"""Reporter module for the mini-project.

This module reads the parsed dictionary and statistics from the parser and analyzer
modules, formats them into a human-readable report, and exposes a generate_report()
method that returns the report string.
"""

from typing import Dict, Any


def generate_report(parsed_dict: Dict[str, Any], stats: Dict[str, Any]) -> str:
    """Generate a human-readable report from parsed data and statistics.

    Args:
        parsed_dict: Dictionary containing parsed data from the input file.
        stats: Dictionary containing statistics about the parsed data.

    Returns:
        A string containing the formatted report.
    """
    report_lines = []
    report_lines.append("=== Report ===")
    report_lines.append(f"Total entries: {stats.get('total_entries', 0)}")
    report_lines.append(f"Average value: {stats.get('average_value', 0):.2f}")
    report_lines.append(f"Max value: {stats.get('max_value', 0)}")
    report_lines.append(f"Min value: {stats.get('min_value', 0)}")
    report_lines.append("")
    report_lines.append("Parsed Data:")
    for key, value in parsed_dict.items():
        report_lines.append(f"  {key}: {value}")
    report_lines.append("")
    report_lines.append("Statistics:")
    for key, value in stats.items():
        report_lines.append(f"  {key}: {value}")
    report_lines.append("=== End Report ===")
    return "\n".join(report_lines)


if __name__ == "__main__":
    # Example usage
    sample_parsed_dict = {
        "name": "John Doe",
        "age": 30,
        "email": "john.doe@example.com"
    }
    sample_stats = {
        "total_entries": 1,
        "average_value": 30.0,
        "max_value": 30,
        "min_value": 30
    }
    print(generate_report(sample_parsed_dict, sample_stats))
