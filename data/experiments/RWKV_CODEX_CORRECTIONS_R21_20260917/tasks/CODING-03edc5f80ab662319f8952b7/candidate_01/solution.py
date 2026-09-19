import sys
out=[]
for token in sys.stdin.buffer.read().split():
 if token==b'*':break
 s=token.decode()
 if s.isdigit():
  number=int(s);x=number;letters=[]
  while x:
   x,r=divmod(x-1,26);letters.append(chr(97+r))
  word=''.join(reversed(letters))
 else:
  word=s;number=0
  for c in word:number=number*26+ord(c)-96
 out.append(f'{word:<22}{number:,}')
print('\n'.join(out))
