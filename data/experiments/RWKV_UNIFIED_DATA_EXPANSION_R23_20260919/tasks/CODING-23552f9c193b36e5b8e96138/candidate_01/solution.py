import sys
N,M,K=map(int,sys.stdin.buffer.read().split());P=1000000007;L=M+K
inverse=[0]*(L+1);inverse[1]=1
for i in range(2,L+1):inverse[i]=P-(P//i)*inverse[P%i]%P
invfact=[1]*(L+1)
for i in range(1,L+1):invfact[i]=invfact[i-1]*inverse[i]%P
coefficient=1;weight=pow(3,L,P);answer=weight;third=pow(3,P-2,P)
for i in range(L):
 value=2*coefficient
 if 0<=i-M<=K:value-=invfact[M]*invfact[i-M]
 if 0<=i-K<=M:value-=invfact[K]*invfact[i-K]
 coefficient=value*inverse[i+1]%P
 weight=weight*(N+i)%P*third%P
 answer=(answer+weight*coefficient)%P
print(answer)
