import sys
s=sys.stdin.buffer.read().strip();dp=[[0,0] for _ in range(26)];answer=0
for i,c in enumerate(s):
 row=dp[c-65];parity=i&1;row[parity]=max(row[parity],row[parity^1]+1);answer=max(answer,row[parity])
print(answer)
