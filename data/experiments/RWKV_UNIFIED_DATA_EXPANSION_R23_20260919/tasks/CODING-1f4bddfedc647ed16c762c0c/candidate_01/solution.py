import sys
v=sys.stdin.read().split();n=int(v[0]);s=v[1];runs=[];days=n;i=0
while i<n:
 if s[i]=='0':i+=1;continue
 j=i
 while j<n and s[j]=='1':j+=1
 length=j-i;runs.append(length);days=min(days,length-1 if i==0 or j==n else (length-1)//2);i=j
width=2*days+1;print(sum((length+width-1)//width for length in runs))
