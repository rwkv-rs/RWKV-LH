import sys
v=iter(map(int,sys.stdin.read().split()));out=[];case=0
for n in v:
 if n==0:break
 heights=[next(v) for _ in range(n)];average=sum(heights)//n;moves=sum(max(0,h-average) for h in heights);case+=1;out.append(f'Set #{case}\nThe minimum number of moves is {moves}.')
print('\n\n'.join(out))
