import sys
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];points=list(zip(v[1::2],v[2::2]));residue=0;modulus=1
for degree,poly in ((7,0x83),(8,0x11d),(9,0x211),(11,0x805),(13,0x201b),(17,0x20009)):
 size=1<<degree;period=size-1;exps=[0]*period;logs=[0]*size;a=1
 for i in range(period):
  exps[i]=a;logs[a]=i;a<<=1
  if a&size:a^=poly
 factor=logs[3];total=0
 for x,y in points:total^=exps[(x+factor*y)%period]
 r=logs[total];step=(r-residue)*pow(modulus,-1,period)%period;residue+=modulus*step;modulus*=period
 lower=min(x for x,y in points);upper=max(x+y for x,y in points)
answer=residue+(lower-residue+modulus-1)//modulus*modulus
print(answer)
