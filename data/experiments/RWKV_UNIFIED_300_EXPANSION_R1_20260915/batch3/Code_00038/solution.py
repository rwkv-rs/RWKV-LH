import sys
a=iter(map(int,sys.stdin.buffer.read().split()));k,q=next(a),next(a);d=[next(a) for _ in range(k)];out=[]
for _ in range(q):
    n,x,m=next(a),next(a),next(a);whole,part=divmod(n-1,k);rem=[v%m for v in d]
    total=sum(rem)*whole+sum(rem[:part]);zeros=rem.count(0)*whole+rem[:part].count(0)
    out.append(str(n-1-zeros-(x%m+total)//m))
print(*out, sep=chr(10))
