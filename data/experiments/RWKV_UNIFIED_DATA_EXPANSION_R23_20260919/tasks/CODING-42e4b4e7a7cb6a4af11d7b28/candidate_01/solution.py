import sys,re
pattern=re.compile(r'[+-]?[0-9]+(?:\.[0-9]+(?:[eE][+-]?[0-9]+)?|[eE][+-]?[0-9]+)')
for line in sys.stdin:
 s=line.strip()
 if s=='*':break
 print(s+' is '+('legal.' if pattern.fullmatch(s) else 'illegal.'))
