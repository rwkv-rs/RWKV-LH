import sys,re
s=sys.stdin.read();out=[];enabled=True;i=0
while i<len(s):
 if s[i]!='\\' or i+1==len(s):out.append(s[i]);i+=1;continue
 c=s[i+1]
 if c=='*':enabled=not enabled;i+=2
 elif not enabled:out.append(s[i]);i+=1
 elif c in 'bi':i+=2
 elif c=='\\':out.append('\\');i+=2
 elif c=='s':
  i+=2;m=re.match(r'(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)',s[i:])
  if m:i+=len(m.group())
 else:out.append(s[i]);i+=1
sys.stdout.write(''.join(out))
