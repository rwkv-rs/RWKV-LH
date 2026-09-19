import sys
terms=sys.stdin.read().strip().split('|');pos={x for x in terms if not x.startswith('~')};neg={x[1:] for x in terms if x.startswith('~')};print((1<<len(pos|neg))-(0 if pos&neg else 1))
