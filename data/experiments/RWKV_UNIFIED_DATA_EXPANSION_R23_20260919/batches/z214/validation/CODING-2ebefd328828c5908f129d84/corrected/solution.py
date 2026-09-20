import sys
small=[]
for i in range(5):
 for a in range(1,16):small.append((a<<(4*i),1))
 for j in range(i):
  for a in range(1,16):
   for b in range(1,16):small.append(((a<<(4*i))|(b<<(4*j)),2))
basis=[]
for bit in range(20):
 leading=1<<bit;rows=set();cols=set();pairs=set()
 for delta,weight in small:
  if delta>>bit!=1:continue
  previous=delta^leading;parity=0
  while previous:
   low=previous&-previous;parity^=basis[low.bit_length()-1];previous-=low
  if weight==1:rows.add(parity>>4);cols.add(parity&15)
  else:pairs.add(parity)
 for parity in range(256):
  if parity>>4 not in rows and parity&15 not in cols and parity not in pairs:basis.append(parity);break
 else:raise RuntimeError('no systematic code extension')
prefix=int(sys.stdin.buffer.read())-1;parity=0;x=prefix
while x:
 low=x&-x;parity^=basis[low.bit_length()-1];x-=low
print(format((prefix<<8)|parity,'07x'))
