import sys
s=sys.stdin.read().strip();mod=998244353;q=s.count('?');inverse=[1]*(q+2)
for i in range(2,q+2):inverse[i]=mod-(mod//i)*inverse[mod%i]%mod
def tails(n):
 if n<0:return []
 a=[1]*(n+2);a[-1]=0
 for i in range(1,n+1):a[i]=a[i-1]*(n-i+1)%mod*inverse[i]%mod
 for i in range(n-1,-1,-1):a[i]=(a[i]+a[i+1])%mod
 return a
all_tail=tails(q);forced_tail=tails(q-1);left_open=left_unknown=0;right_close=s.count(')');answer=0
for c in s:
 if c==')':right_close-=1;continue
 needed=left_open+left_unknown+1-right_close;table=all_tail if c=='(' else forced_tail
 if needed<len(table):answer=(answer+table[max(0,needed)])%mod
 if c=='(':left_open+=1
 else:left_unknown+=1
print(answer)
