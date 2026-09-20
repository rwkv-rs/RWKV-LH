import sys
v=list(map(int,sys.stdin.buffer.read().split()));p=0;out=[]
while p<len(v):
 n=v[p];p+=1
 if n==0:break
 prices=v[p:p+n];p+=n;dp={0:(0,0)}
 for price in prices:
  change=(-price)%1000;updated=dp.copy()
  for coins,(saved,cost) in dp.items():
   gain=int(coins+change>=500);remaining=coins+change-500*gain;candidate=(saved+gain,cost+price);old=updated.get(remaining)
   if old is None or candidate[0]>old[0] or (candidate[0]==old[0] and candidate[1]<old[1]):updated[remaining]=candidate
  dp=updated
 saved,cost=max(dp.values(),key=lambda p:(p[0],-p[1]));out.append(f'{saved} {cost}')
print('\n'.join(out))
