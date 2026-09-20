import sys,re,bisect
v=sys.stdin.buffer.read().split();text=v[1];q=int(v[2]);matches=list(re.finditer(rb'[0-9]+',text));starts=[m.start() for m in matches];ends=[m.end() for m in matches];numbers=[int(m.group()) for m in matches];ops=[text[ends[i]:starts[i+1]] for i in range(len(numbers)-1)];xor_prefix=[0]
for x in numbers:xor_prefix.append(xor_prefix[-1]^x)
xstart=[0];xend=[];xid=[0]*len(numbers);separators=[]
for i,op in enumerate(ops):
 if op!=b'^':xend.append(i);xstart.append(i+1);separators.append(op)
 xid[i+1]=len(xstart)-1
xend.append(len(numbers)-1);xvalues=[xor_prefix[r+1]^xor_prefix[l] for l,r in zip(xstart,xend)];astart=[0];aend=[];aid=[0]*len(xvalues)
for i,op in enumerate(separators):
 if op==b'|':aend.append(i);astart.append(i+1)
 aid[i+1]=len(astart)-1
aend.append(len(xvalues)-1);MASK=(1<<31)-1
class Tree:
 def __init__(self,values,is_and):
  self.is_and=is_and;self.identity=MASK if is_and else 0;self.size=1
  while self.size<len(values):self.size*=2
  self.data=[self.identity]*(2*self.size);self.data[self.size:self.size+len(values)]=values
  for i in range(self.size-1,0,-1):self.data[i]=(self.data[2*i]&self.data[2*i+1]) if is_and else (self.data[2*i]|self.data[2*i+1])
 def query(self,l,r):
  value=self.identity;l+=self.size;r+=self.size
  while l<r:
   if l&1:value=(value&self.data[l]) if self.is_and else (value|self.data[l]);l+=1
   if r&1:r-=1;value=(value&self.data[r]) if self.is_and else (value|self.data[r])
   l//=2;r//=2
  return value
andt=Tree(xvalues,True);avalues=[andt.query(l,r+1) for l,r in zip(astart,aend)];ort=Tree(avalues,False);out=[]
for l,r in zip(map(int,v[3::2]),map(int,v[4::2])):
 a=bisect.bisect_right(starts,l)-1;b=bisect.bisect_right(starts,r)-1
 if a==b:out.append(str(int(text[l:r+1])));continue
 first=int(text[l:ends[a]]);last=int(text[starts[b]:r+1]);u=xid[a];w=xid[b]
 if u==w:answer=xor_prefix[b+1]^xor_prefix[a]^numbers[a]^first^numbers[b]^last
 else:
  left=xor_prefix[xend[u]+1]^xor_prefix[a]^numbers[a]^first;right=xor_prefix[b+1]^xor_prefix[xstart[w]]^numbers[b]^last;g=aid[u];h=aid[w]
  if g==h:answer=left&right&andt.query(u+1,w)
  else:answer=(left&andt.query(u+1,aend[g]+1))|(right&andt.query(astart[h],w))|ort.query(g+1,h)
 out.append(str(answer))
print('\n'.join(out))
