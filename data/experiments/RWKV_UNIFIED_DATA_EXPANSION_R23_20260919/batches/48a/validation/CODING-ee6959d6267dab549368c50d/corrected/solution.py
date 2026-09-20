import sys
v=sys.stdin.buffer.read().split();t,k=map(int,v[:2]);pairs=[(v[i].decode(),v[i+1].decode()) for i in range(2,len(v),2)];length=max(len(r) for l,r in pairs);MOD=1000000007;k=min(k,length);dp=[[1]*(k+1)]
for m in range(1,length+1):
 old=dp[-1];row=[0]*(k+1);row[0]=(8*old[0]+2*old[k])%MOD
 for cool in range(1,k+1):row[cool]=8*old[cool-1]%MOD
 dp.append(row)
def nearly(text):
 cool=0;safe=0;valid=True;value=0
 for ch in text:value=(value*10+int(ch))%MOD
 for i,ch in enumerate(text):
  d=int(ch);remaining=len(text)-i-1;lucky=(d>4)+(d>7);safe=(safe+(d-lucky)*dp[remaining][max(0,cool-1)])%MOD
  if cool==0:safe=(safe+lucky*dp[remaining][k])%MOD
  if d in (4,7):
   if cool:valid=False;break
   cool=k
  else:cool=max(0,cool-1)
 if valid:safe=(safe+1)%MOD
 return (value+1-safe)%MOD,not valid
out=[]
for l,r in pairs:
 R,_=nearly(r);L,is_lucky=nearly(l);out.append(str((R-L+is_lucky)%MOD))
print('\n'.join(out))
