import sys
P=10**9+7
words=sys.stdin.buffer.read().split();n=int(words[0]);previous=b'';positions=[0];ways=[1]
def ordered_cuts(word):
 descending=[];ascending=[]
 for i in range(len(word)-1):
  if word[i]>word[i+1]:descending.append(i)
  elif word[i]<word[i+1]:ascending.append(i)
 return descending+[len(word)-1,len(word)]+ascending[::-1]
def variant(word,cut):return word if cut==len(word) else word[:cut]+word[cut+1:]
for word in words[1:n+1]:
 cuts=ordered_cuts(word);current=[];at=0;total=0;before=variant(previous,positions[0])
 for cut in cuts:
  after=variant(word,cut)
  while at<len(positions) and before<=after:
   total=(total+ways[at])%P;at+=1
   if at<len(positions):before=variant(previous,positions[at])
  current.append(total)
 previous=word;positions=cuts;ways=current
print(sum(ways)%P)
