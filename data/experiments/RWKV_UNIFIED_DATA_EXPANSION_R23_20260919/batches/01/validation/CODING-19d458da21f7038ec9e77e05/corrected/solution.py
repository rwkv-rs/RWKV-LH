import sys
v=sys.stdin.read().split();words=[]
for word in v[1:]:
 mask=0
 for ch in word:mask|=1<<(ord(ch)-97)
 words.append(mask)
words.sort(key=int.bit_count,reverse=True);n=len(words);suffix=[0]*(n+1)
for i in range(n-1,-1,-1):suffix[i]=suffix[i+1]|words[i]
full=(1<<26)-1
def count(i,have):
 if have==full:return 1<<(n-i)
 if i==n or have|suffix[i]!=full:return 0
 return count(i+1,have|words[i])+count(i+1,have)
print(count(0,0))
