import sys
v=sys.stdin.read().split();out=[]
for s in v[1:1+int(v[0])]:
 alphabet={c:i for i,c in enumerate(sorted(set(s)))};width=len(alphabet);single=0;pairs=0;triples=[0]*width
 for char in s:
  c=alphabet[char];triples[c]|=pairs;pairs|=single<<(c*width);single|=1<<c
 out.append(str(sum(x.bit_count() for x in triples)))
print('\n'.join(out))
