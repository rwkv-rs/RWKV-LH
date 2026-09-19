import sys
lines=sys.stdin.read().splitlines();out=[];mod=1000000007
for s in lines[1:1+int(lines[0])]:
 total=1;previous={}
 for c in s:
  old=total;total=(2*total-previous.get(c,0))%mod;previous[c]=old
 out.append(str(total))
print('\n'.join(out))
