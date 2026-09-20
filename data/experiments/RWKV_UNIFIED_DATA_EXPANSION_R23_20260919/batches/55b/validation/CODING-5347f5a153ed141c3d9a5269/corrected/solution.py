import sys,re
v=iter(re.findall(r'[0-9]+|[+*/=-]',sys.stdin.read()));out=[]
for _ in range(int(next(v))):
 token=next(v);value=-int(next(v)) if token=='-' else int(token)
 while True:
  op=next(v)
  if op=='=':break
  token=next(v);x=-int(next(v)) if token=='-' else int(token)
  if op=='+':value+=x
  elif op=='-':value-=x
  elif op=='*':value*=x
  else:value=(abs(value)//abs(x))*(-1 if (value<0)!=(x<0) else 1)
 out.append(str(value))
print('\n'.join(out))
