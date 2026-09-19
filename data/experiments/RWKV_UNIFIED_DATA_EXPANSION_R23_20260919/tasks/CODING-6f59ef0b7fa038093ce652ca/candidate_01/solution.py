import sys,re
v=sys.stdin.read().split();out=[];count=0
for token in v[1:]:
 word=token.rstrip('.?!')
 if re.fullmatch('[A-Z][a-z]*',word):count+=1
 if token[-1] in '.?!':out.append(str(count));count=0
print('\n'.join(out))
