import sys
v=iter(sys.stdin.buffer.read().split());out=[];case=0
for token in v:
 d=int(token)
 if not d:break
 s,b=int(next(v)),int(next(v));parity=next(v);rows=[list(next(v).decode()) for _ in range(d)];wanted=0 if parity==b'E' else 1;valid=True
 for j in range(s*b):
  unknown=[];value=0
  for i in range(d):
   if rows[i][j] in '01':value^=int(rows[i][j])
   else:unknown.append(i)
  if len(unknown)>1 or (not unknown and value!=wanted):valid=False;break
  if unknown:rows[unknown[0]][j]=str(value^wanted)
 case+=1
 if not valid:out.append(f'Disk set {case} is invalid.');continue
 bits=''.join(''.join(rows[disk][block*s:(block+1)*s]) for block in range(b) for disk in range(d) if disk!=block%d);bits+='0'*((-len(bits))%4);hexadecimal=''.join(format(int(bits[i:i+4],2),'X') for i in range(0,len(bits),4));out.append(f'Disk set {case} is valid, contents are: {hexadecimal}')
print('\n'.join(out))
