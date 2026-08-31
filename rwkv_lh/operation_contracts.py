"""Authoritative structural contracts shared by Harness and Selector feedback."""

from __future__ import annotations


PATH_MUTATION_ARGUMENTS: dict[str, tuple[str, ...]] = {
    "write_file": ("path",),
    "write_json": ("path",),
    "patch_json": ("path",),
    "replace_text": ("path",),
    "remove_line": ("path",),
    "append_file": ("path",),
    "delete_file": ("path",),
    "make_directory": ("path",),
    "copy_file": ("destination",),
    "move_file": ("source", "destination"),
}
PATH_MUTATION_OPERATIONS = frozenset(PATH_MUTATION_ARGUMENTS)
JSON_PATH_OPERATIONS = frozenset({"read_json", "write_json", "patch_json"})
TEXT_PATH_OPERATIONS = frozenset(
    {"read_file", "write_file", "replace_text", "remove_line", "append_file"}
)


__all__ = [
    "JSON_PATH_OPERATIONS",
    "PATH_MUTATION_ARGUMENTS",
    "PATH_MUTATION_OPERATIONS",
    "TEXT_PATH_OPERATIONS",
]
