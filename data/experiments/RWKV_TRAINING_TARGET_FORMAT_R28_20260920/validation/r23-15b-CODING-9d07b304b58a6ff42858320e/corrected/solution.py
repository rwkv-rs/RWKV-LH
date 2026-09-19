import sys
out=[]
for line in sys.stdin:
 s=line.rstrip('\r\n')
 if s and s.isdigit():
  s=s[::-1];i=0;chars=[]
  while i<len(s):
   k=3 if s[i]=='1' else 2;chars.append(chr(int(s[i:i+k])));i+=k
  out.append(''.join(chars))
 else:out.append(''.join(str(ord(c)) for c in s)[::-1])
print('\n'.join(out))
