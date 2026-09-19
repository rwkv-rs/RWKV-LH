import sys
v=iter(sys.stdin.read().split());out=[]
for case in range(1,int(next(v))+1):
 n=int(next(v));groups=[]
 for _ in range(n):
  names={}
  for j in range(int(next(v))):
   word=next(v).capitalize();letter=ord(word[0])-65
   if letter<n:names[letter]=word
  groups.append(names)
 match=[-1]*n
 def augment(g,seen):
  for c in groups[g]:
   if c in seen:continue
   seen.add(c)
   if match[c]<0 or augment(match[c],seen):match[c]=g;return True
  return False
 for g in range(n):augment(g,set())
 out.append(f'Case #{case}:');out.extend(groups[match[c]][c] for c in range(n))
print('\n'.join(out))
