import sys
v=list(map(int,sys.stdin.read().split()));n=v[0];a=v[1:];total=0;minimum=10**30;best_num=-1;best_den=1;answer=[]
for k in range(n-1,0,-1):
 total+=a[k];minimum=min(minimum,a[k]);den=n-k-1
 if den==0:continue
 num=total-minimum;delta=num*best_den-best_num*den
 if delta>0:best_num=num;best_den=den;answer=[k]
 elif delta==0:answer.append(k)
print('\n'.join(map(str,reversed(answer)))))
