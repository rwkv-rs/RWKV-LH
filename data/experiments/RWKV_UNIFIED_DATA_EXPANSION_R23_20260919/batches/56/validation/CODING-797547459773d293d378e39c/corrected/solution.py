import sys
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];a=v[1:];left=[0]*n;right=[n]*n;stack=[]
for i,x in enumerate(a):
 while stack and a[stack[-1]]<=x:stack.pop()
 left[i]=stack[-1] if stack else -1;stack.append(i)
stack=[]
for i in range(n-1,-1,-1):
 while stack and a[stack[-1]]<a[i]:stack.pop()
 right[i]=stack[-1] if stack else n;stack.append(i)
slope=[0]*(n+2);intercept=[0]*(n+2)
def add(l,r,k,b):
 if l<=r:slope[l]+=k;slope[r+1]-=k;intercept[l]+=b;intercept[r+1]-=b
for i,x in enumerate(a):
 l=i-left[i];r=right[i]-i;l,r=min(l,r),max(l,r);add(1,l,x,0);add(l+1,r,0,x*l);add(r+1,l+r-1,-x,x*(l+r))
k=b=0;out=[]
for length in range(1,n+1):k+=slope[length];b+=intercept[length];out.append(str(k*length+b))
print('\n'.join(out))
