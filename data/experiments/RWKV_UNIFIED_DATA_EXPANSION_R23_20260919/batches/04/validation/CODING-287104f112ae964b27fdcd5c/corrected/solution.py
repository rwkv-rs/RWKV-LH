import sys
s=sys.stdin.read().strip();smallest='z';out=[]
for c in s:
 out.append('Ann' if c>smallest else 'Mike');smallest=min(smallest,c)
print('\n'.join(out))
