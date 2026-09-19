import sys
out=[]
for s in sys.stdin.read().split():
 valid=len(s)==len(set(s)) and all('a'<=c<='z' or '0'<=c<='9' for c in s);out.append('Valid' if valid else 'Invalid')
 if valid:break
print('\n'.join(out))
