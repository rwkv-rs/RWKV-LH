import sys,math
MOD=998244353

def count_pair(n,p,q):
 bound=n//q
 if not bound:return 0
 witnesses=9//q;full=(1<<witnesses)-1;good=1<<(2*witnesses)
 xm=[0]*10;ym=[0]*10
 for j in range(witnesses):xm[p*(j+1)]=1<<j;ym[q*(j+1)]=(1<<j)<<witnesses
 # State is the multiplication carries and the set of witnessed nonzero digits.
 states=[(0,0,0)];lookup={states[0]:0};trans=[];at=0
 while at<len(states):
  a,b,mask=states[at];row=[]
  for digit in range(10):
   u=a+p*digit;v=b+q*digit
   value=good if mask==good else mask|xm[u%10]|ym[v%10]
   if value!=good and (value&full)&(value>>witnesses):value=good
   key=(u//10,v//10,value)
   idx=lookup.get(key)
   if idx is None:idx=len(states);lookup[key]=idx;states.append(key)
   row.append(idx)
  trans.append(row);at+=1
 size=len(states);dp={0:1}
 for limit in map(int,reversed(str(bound))):
  nxt={}
  for packed,number in dp.items():
   state=packed>>1;borrow=packed&1
   for digit,target in enumerate(trans[state]):
    key=2*target+int(digit>limit or (digit==limit and borrow))
    nxt[key]=(nxt.get(key,0)+number)%MOD
  dp=nxt
 answer=0
 for packed,number in dp.items():
  if packed&1:continue
  a,b,mask=states[packed>>1]
  if mask!=good:
   while a or b:mask|=xm[a%10]|ym[b%10];a//=10;b//=10
  if mask==good or (mask&full)&(mask>>witnesses):answer+=number
 return answer%MOD
n=int(sys.stdin.buffer.read());answer=n%MOD
for q in range(2,10):
 for p in range(1,q):
  if math.gcd(p,q)==1:answer=(answer+2*count_pair(n,p,q))%MOD
print(answer)
