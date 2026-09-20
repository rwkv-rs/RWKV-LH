import sys
MOD=998244353
v=iter(map(int,sys.stdin.buffer.read().split()));n=next(v);lengths=[next(v) for _ in range(n)];m=next(v);fixed=[{} for _ in range(n)]
for _ in range(m):x=next(v)-1;y=next(v);c=next(v)-1;fixed[x][y]=c
rules=[[next(v) for _ in range(3)] for _ in range(3)]
def step(state,color):
 mask=0
 for value,allowed in zip(state,rules[color]):
  if allowed and value<4:mask|=1<<value
 g=0
 while mask>>g&1:g+=1
 return (g,state[0],state[1])
reachable={(4,4,4)}
for _ in range(3):reachable={step(state,c) for state in reachable for c in range(3)}
states=list(reachable);index={state:i for i,state in enumerate(states)};at=0
while at<len(states):
 state=states[at];at+=1
 for c in range(3):
  child=step(state,c)
  if child not in index:index[child]=len(states);states.append(child)
labels=[state[0] for state in states]
while True:
 lookup={};new=[]
 for state in states:
  key=(state[0],tuple(labels[index[step(state,c)]] for c in range(3)))
  if key not in lookup:lookup[key]=len(lookup)
  new.append(lookup[key])
 if new==labels:break
 labels=new
representatives=[None]*len(set(labels))
for state,label in zip(states,labels):representatives[label]=state
index={state:label for state,label in zip(states,labels)};states=representatives
size=len(states);transitions=[[index[step(state,c)] for state in states] for c in range(3)];matrix=[[0]*size for _ in range(size)]
for source in range(size):
 for c in range(3):matrix[transitions[c][source]][source]+=1
width=((size*(MOD-1)**2).bit_length()+7)//8;stride=size*width

def pack(matrix):return int.from_bytes(b''.join(value.to_bytes(width,'little') for row in matrix for value in row),'little')
def multiply(packed,vector):
 right=int.from_bytes(b''.join(value.to_bytes(width,'little') for value in reversed(vector)),'little');data=(packed*right).to_bytes((size*size+size-1)*width,'little')
 return [int.from_bytes(data[(r+1)*stride-width:(r+1)*stride],'little')%MOD for r in range(size)]
powers=[];power_matrices=[]
def ensure(bit):
 if not powers:powers.append(pack(matrix));power_matrices.append(matrix)
 while len(powers)<=bit:
  previous=power_matrices[-1];columns=[multiply(powers[-1],[row[j] for row in previous]) for j in range(size)];squared=[list(row) for row in zip(*columns)];power_matrices.append(squared);powers.append(pack(squared))
def advance(vector,count):
 bit=0
 while count:
  if count&1:ensure(bit);vector=multiply(powers[bit],vector)
  count>>=1;bit+=1
 return vector
cache={};combined=[1,0,0,0]
for length,colors in zip(lengths,fixed):
 key=(length,tuple(sorted(colors.items())))
 if key in cache:distribution=cache[key]
 else:
  prefix={(4,4,4):1}
  for pos in range(1,min(3,length)+1):
   nxt={}
   for state,count in prefix.items():
    for c in ([colors[pos]] if pos in colors else range(3)):
     child=step(state,c);nxt[child]=(nxt.get(child,0)+count)%MOD
   prefix=nxt
  distribution=[0]*4
  if length<=3:
   for state,count in prefix.items():distribution[state[0]]=(distribution[state[0]]+count)%MOD
  else:
   vector=[0]*size
   for state,count in prefix.items():vector[index[state]]=(vector[index[state]]+count)%MOD
   previous=3
   for pos,c in sorted(colors.items()):
    if pos<=3:continue
    vector=advance(vector,pos-previous-1);nxt=[0]*size
    for i,count in enumerate(vector):j=transitions[c][i];nxt[j]=(nxt[j]+count)%MOD
    vector=nxt;previous=pos
   vector=advance(vector,length-previous)
   for state,count in zip(states,vector):distribution[state[0]]=(distribution[state[0]]+count)%MOD
  cache[key]=distribution
 combined=[sum(combined[j]*distribution[i^j] for j in range(4))%MOD for i in range(4)]
print(combined[0])
