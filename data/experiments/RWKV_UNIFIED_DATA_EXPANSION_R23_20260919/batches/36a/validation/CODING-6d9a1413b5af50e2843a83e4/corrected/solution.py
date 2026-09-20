import sys
v=sys.stdin.buffer.read().split();number=v[0].decode();mapping={c:str(d) for d,s in enumerate(('ABC','DEF','GHI','JKL','MNO','PRS','TUV','WXY'),2) for c in s}
names=sorted({name.decode() for name in v[1:] if len(name)==len(number) and ''.join(mapping.get(chr(c),'?') for c in name)==number})
print('\n'.join(names) if names else 'NONE')
