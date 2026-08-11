def slugify(value: str) -> str:
    if not value:
        return ''
    value = value.lower()
    value = ''.join(c if c.isalnum() or c in (' ', '-', '_') else '-' for c in value)
    value = value.strip('-')
    value = '-'.join(part for part in value.split('-') if part)
    return value