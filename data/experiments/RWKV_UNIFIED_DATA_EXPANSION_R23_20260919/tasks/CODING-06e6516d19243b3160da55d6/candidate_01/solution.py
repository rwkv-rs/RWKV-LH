import sys
out=[]
for word in sys.stdin.read().split():
 palindromes=set();n=len(word)
 for center in range(2*n-1):
  left=center//2;right=left+center%2
  while left>=0 and right<n and word[left]==word[right]:
   if right-left+1>=3:palindromes.add(word[left:right+1])
   left-=1;right+=1
 ordered=sorted(palindromes,key=lambda s:(-len(s),s))
 if any(short not in long for long,short in zip(ordered,ordered[1:])):out.append(word)
print('\n'.join(out))
