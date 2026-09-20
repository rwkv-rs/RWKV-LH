import sys
it=iter(map(int,sys.stdin.buffer.read().split()));out=[]
for _ in range(next(it)):
 schools,chosen,n=next(it),next(it),next(it);pages=[next(it) for i in range(n)];small,large_count=divmod(n,schools)
 start=chosen*small+min(chosen,large_count);count=small+(chosen<large_count);ordered=sorted(range(n),key=lambda i:(pages[i],i));first=min(ordered[start:start+count]);out.append(str(pages[first]))
print('\n'.join(out))
