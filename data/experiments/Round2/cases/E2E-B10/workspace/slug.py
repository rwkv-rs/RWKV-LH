def slugify(value: str) -> str:
    if value is None:
        return ""
    value = str(value).strip()
    if not value:
        return ""
    value = value.lower()
    value = re.sub(r'[^a-z0-9]+', '-', value)
    value = value.strip('-')
    return value