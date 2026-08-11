def slugify(value: str) -> str:
    if not value:
        return ''
    
    # Convert to lowercase
    value = value.lower()
    
    # Replace non-alphanumeric characters with hyphens
    value = ''.join(c if c.isalnum() else '-' for c in value)
    
    # Remove leading/trailing hyphens
    value = value.strip('-')
    
    # Replace multiple hyphens with single hyphen
    value = '-'.join(part for part in value.split('-') if part)
    
    return value