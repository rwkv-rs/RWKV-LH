import sys
rows=[list(map(int,line.strip().split(','))) for line in sys.stdin if line.strip()];dp=rows[0]
for row in rows[1:]:
 if len(row)>len(dp):dp=[x+max(dp[j-1] if j else -10**20,dp[j] if j<len(dp) else -10**20) for j,x in enumerate(row)]
 else:dp=[x+max(dp[j],dp[j+1]) for j,x in enumerate(row)]
print(dp[0])
