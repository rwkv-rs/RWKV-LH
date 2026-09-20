import sys
v=sys.stdin.buffer.read().split();k=int(v[0]);lo=float(v[1]);hi=float(v[2]);p=float(v[3]);e=float(v[4]);target=float(v[5]);left=target-e;right=target+e
stack=[(k,lo,hi,1.0)];answer=0.0
while stack:
 depth,a,b,weight=stack.pop()
 if not weight:continue
 step=(b-a)/(1<<depth);small=a+step/2;large=b-step/2
 if large<left or small>right:continue
 if left<=small and large<=right:answer+=weight;continue
 if depth==0:continue
 mid=(a+b)/2;lower=(1-p) if mid>=target else p
 stack.append((depth-1,a,mid,weight*lower));stack.append((depth-1,mid,b,weight*(1-lower)))
print(f'{answer:.6f}')
