import sys
words=[];case=0;out=[]
for word in sys.stdin.read().split():
 if word=='9':
  case+=1;words.sort();bad=any(words[i+1].startswith(words[i]) for i in range(len(words)-1));out.append(f'Set {case} is '+('not ' if bad else '')+'immediately decodable');words=[]
 else:words.append(word)
print('\n'.join(out))
