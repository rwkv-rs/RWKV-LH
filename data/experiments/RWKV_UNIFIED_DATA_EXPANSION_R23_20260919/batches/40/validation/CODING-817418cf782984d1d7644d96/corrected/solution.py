import sys
codes=['.-','-...','-.-.','-..','.','..-.','--.','....','..','.---','-.-','.-..','--','-.','---','.--.','--.-','.-.','...','-','..-','...-','.--','-..-','-.--','--..'];it=iter(sys.stdin.buffer.read().split());out=[]
for _ in range(int(next(it))):
 message=next(it).decode();n=int(next(it));nodes=[{}];ends=[0]
 for __ in range(n):
  word=next(it).decode();encoded=''.join(codes[ord(c)-65] for c in word);u=0
  for c in encoded:
   if c not in nodes[u]:nodes[u][c]=len(nodes);nodes.append({});ends.append(0)
   u=nodes[u][c]
  ends[u]+=1
 dp=[0]*(len(message)+1);dp[0]=1
 for i in range(len(message)):
  if not dp[i]:continue
  u=0
  for j in range(i,len(message)):
   if message[j] not in nodes[u]:break
   u=nodes[u][message[j]]
   if ends[u]:dp[j+1]+=dp[i]*ends[u]
 out.append(str(dp[-1]))
print('\n'.join(out))
