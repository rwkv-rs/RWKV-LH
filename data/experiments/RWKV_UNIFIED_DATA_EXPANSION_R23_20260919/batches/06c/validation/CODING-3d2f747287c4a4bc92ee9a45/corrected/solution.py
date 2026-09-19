import sys,re
sys.stdout.write(re.sub(r'\S+',lambda match:match.group(0)[::-1],sys.stdin.read()))
