import sys,itertools
lines=iter(sys.stdin.read().splitlines());out=[];case=0;names=('divine','evil','human')
for line in lines:
 if not line.strip():continue
 n=int(line)
 if n==0:break
 case+=1;statements=[]
 for _ in range(n):
  text=next(lines).strip().rstrip('.');speaker=ord(text[0])-65;words=text[3:].split();negative='not' in words
  if words[0]=='It':statements.append((speaker,-1,words[-1],negative))
  else:statements.append((speaker,speaker if words[0]=='I' else ord(words[0])-65,words[-1],negative))
 valid=[]
 for types in itertools.product(range(3),repeat=5):
  for day in (False,True):
   truthful=[kind==0 or (kind==2 and day) for kind in types];good=True
   for speaker,subject,predicate,negative in statements:
    if subject<0:claim=day if predicate=='day' else not day
    elif predicate=='lying':claim=not truthful[subject]
    else:claim=names[types[subject]]==predicate
    if negative:claim=not claim
    if claim!=truthful[speaker]:good=False;break
   if good:valid.append((types,day))
 out.append('Conversation #'+str(case))
 if not valid:out.append('This is impossible.');continue
 facts=[]
 for i in range(5):
  values={types[i] for types,day in valid}
  if len(values)==1:facts.append(chr(65+i)+' is '+names[values.pop()]+'.')
 days={day for types,day in valid}
 if len(days)==1:facts.append('It is '+('day' if days.pop() else 'night')+'.')
 out.extend(facts or ['No facts are deducible.'])
print('\n'.join(out))
