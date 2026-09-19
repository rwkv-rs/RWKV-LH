import sys
v=sys.stdin.read().split();n,m=map(int,v[:2]);special=set(map(int,v[2:2+n]));posts=[]
for i in range(m):
 f,p,s=v[2+n+3*i:5+n+3*i];posts.append((int(f) in special,int(p),s))
posts.sort(reverse=True);print('\n'.join(s for _,_,s in posts))
