import sys
source=sys.stdin.buffer.read()
sys.stdout.buffer.write(bytes(c if c in (10,13) else c-7 for c in source))
