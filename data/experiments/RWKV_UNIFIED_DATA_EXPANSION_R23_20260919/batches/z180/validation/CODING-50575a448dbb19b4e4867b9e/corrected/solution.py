import sys
P=10**9+7
words=sys.stdin.buffer.read().split();n=int(words[0]);previous=b'';positions=[(0,1)];ways=[1]
def ordered_cuts(word):
 descending=[];ascending=[];start=0
 for i in range(len(word)-1):
  if word[i]!=word[i+1]:
   entry=(i,i-start+1);start=i+1
   if word[i]>word[i+1]:descending.append(entry)
   else:ascending.append(entry)
 return descending+[(len(word)-1,len(word)-start),(len(word),1)]+ascending[::-1]
def variant(word,cut):return word if cut==len(word) else word[:cut]+word[cut+1:]
for word in words[1:n+1]:
 cuts=ordered_cuts(word);current=[];at=0;total=0;before=variant(previous,positions[0][0])
 for cut,multiplicity in cuts:
  after=variant(word,cut)
  while at<len(positions) and before<=after:
   total=(total+ways[at])%P;at+=1
   if at<len(positions):before=variant(previous,positions[at][0])
  current.append(total*multiplicity%P)
 previous=word;positions=cuts;ways=current
print(sum(ways)%P)
