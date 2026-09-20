import sys
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];p=1;size=1
while size<n:size*=2
a=[1]*(2*size);b=[0]*(2*size);d=[0]*(2*size);e=[0]*(2*size);root=[0]*(n+1);kind=[0]*(n+1);active=bytearray(n+1);out=[]
for i in range(1,n+1):
 op=v[p];p+=1
 if op==3:base=root[v[p]];p+=1;root[i]=base
 else:base=i;root[i]=i;kind[i]=op
 active[base]^=1;j=size+base-1
 if not active[base]:a[j],b[j],d[j],e[j]=1,0,0,0
 elif kind[base]==1:a[j],b[j],d[j],e[j]=1,1,1,1
 else:a[j],b[j],d[j],e[j]=0,1,0,1
 j//=2
 while j:
  l,r=j*2,j*2+1;a[j]=a[r]*a[l];b[j]=a[r]*b[l]+b[r];d[j]=d[l]+d[r]*a[l];e[j]=e[l]+d[r]*b[l]+e[r];j//=2
 out.append(str(1+d[1]+e[1]))
print('\n'.join(out))
