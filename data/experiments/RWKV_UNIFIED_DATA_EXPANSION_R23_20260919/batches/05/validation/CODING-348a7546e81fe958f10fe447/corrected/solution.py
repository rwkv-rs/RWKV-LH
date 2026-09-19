import sys
v=sys.stdin.read().split();at=0;out=[]
def ip(s):
 result=0
 for x in s.split('.'):result=(result<<8)|int(x)
 return result
def fmt(x):return '.'.join(str((x>>shift)&255) for shift in (24,16,8,0))
while at<len(v):
 n=int(v[at]);at+=1;addresses=[ip(s) for s in v[at:at+n]];at+=n;low=min(addresses);high=max(addresses);bits=(low^high).bit_length();mask=((1<<32)-1)^((1<<bits)-1);out.extend((fmt(low&mask),fmt(mask)))
print('\n'.join(out))
