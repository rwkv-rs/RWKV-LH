import sys
v=sys.stdin.read().split();n=int(v[0]);k=int(v[1]);s=v[2];forced=possible=long_forced=long_possible=0
for c in s:
 forced=forced+1 if c=='N' else 0;possible=possible+1 if c!='Y' else 0
 long_forced=max(long_forced,forced);long_possible=max(long_possible,possible)
print('YES' if long_forced<=k<=long_possible else 'NO')
