def parse_lines(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines