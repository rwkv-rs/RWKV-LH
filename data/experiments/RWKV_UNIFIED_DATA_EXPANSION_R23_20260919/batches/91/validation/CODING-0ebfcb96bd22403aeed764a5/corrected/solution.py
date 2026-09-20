import sys
from array import array
s=sys.stdin.buffer.read().strip();n=len(s);text=bytearray([255])
for i in range(n//2):text.append(s[i]);text.append(s[n-1-i])
MOD=1000000007;length=array('i',[-1,0]);link=array('i',[0,0]);diff=array('i',[0,0]);series=array('i',[0,0]);values=array('I',[0,0]);edges={};last=1;dp=array('I',[0])*(n+1);dp[0]=1
for i in range(1,n+1):
 c=text[i];u=last
 while text[i-1-length[u]]!=c:u=link[u]
 key=u*26+c-97;node=edges.get(key)
 if node is None:
  node=len(length);edges[key]=node;length.append(length[u]+2)
  if length[node]==1:parent=1
  else:
   p=link[u]
   while text[i-1-length[p]]!=c:p=link[p]
   parent=edges[p*26+c-97]
  link.append(parent);difference=length[node]-length[parent];diff.append(difference);series.append(series[parent] if difference==diff[parent] else parent);values.append(0)
 last=node;u=node;total=0
 while length[u]>0:
  value=dp[i-(length[series[u]]+diff[u])]
  if diff[u]==diff[link[u]]:value+=values[link[u]]
  values[u]=value%MOD;total+=values[u];u=series[u]
 if i%2==0:dp[i]=total%MOD
print(dp[n])
