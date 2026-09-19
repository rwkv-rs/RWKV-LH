import sys
v=sys.stdin.read().split();s=v[1];out=[];vowels=set('aeiouy')
for c in s:
 if c in vowels and out and out[-1] in vowels:continue
 out.append(c)
print(''.join(out))
