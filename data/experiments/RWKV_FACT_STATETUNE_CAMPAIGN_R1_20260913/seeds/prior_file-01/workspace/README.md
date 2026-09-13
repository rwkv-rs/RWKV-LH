# Portable team-folder backup

Implement `backup.py` with Python standard library only. Support these commands from any working directory:

- `python backup.py snapshot SOURCE ARCHIVE`
- `python backup.py restore ARCHIVE DESTINATION`

SOURCE is a directory; ARCHIVE must be outside it. Include regular files recursively (including hidden, binary, Unicode names and zero-byte files) and preserve empty directories. Reject symbolic links and other non-regular entries. A failed snapshot must not replace a previous ARCHIVE. Directory/file permissions and timestamps do not need preservation.

Use a ZIP archive with a UTF-8 `manifest.json`: `version` is 1, `directories` lists relative POSIX directory paths, and `files` lists objects with `path`, byte `size`, and lowercase `sha256`. File payloads use ZIP member names `files/<relative path>`. Do not add ZIP directory entries. This is an interoperability format, not an instruction to trust the archive.

Restore must validate version, unique names, declared members, file sizes and digests before replacing DESTINATION. Reject undeclared/duplicate members, absolute paths, parent traversal, backslashes, invalid normalized paths and file/directory conflicts. Symlink destinations are invalid. Existing directory contents are replaced only after complete validation; corrupt input or another failure must leave the previous destination intact. Successful restore must not retain old files. Invalid input must never write outside the destination staging area. Support an empty directory snapshot and restore.

Each successful command writes one JSON object to stdout: `files` and `bytes` count restored/snapshotted regular files and their total original byte size. Failures exit nonzero and explain the problem on stderr. Each invocation is a separate process; no process-memory state is available. Keep staging files beside their final target so replacement can be atomic on the same filesystem. Provide self-authored unit tests and document how to use and validate the utility.
