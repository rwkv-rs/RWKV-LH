import sys
lines=iter(sys.stdin.read().splitlines());count=int(next(lines));output=[]
def swap(subject):return 'you' if subject=='I' else 'I' if subject=='you' else subject
def activity(subject,verb,obj,sign,plural=False):
 if sign<0:phrase=("don't " if subject in ('I','you') or plural else "doesn't ")+verb
 else:phrase=verb+('' if subject in ('I','you') or plural else 's')
 return phrase+(' '+obj if obj else '')
for dialogue in range(1,count+1):
 output.append(f'Dialogue #{dialogue}:');facts=[];contradiction=False
 for line in lines:
  if line.endswith('!'):output.extend([line,'']);break
  body=line[:-1]
  if line.endswith('.'):
   subject,rest=body.split(' ',1);parts=rest.split(' ',1);verb=parts[0];obj=parts[1] if len(parts)>1 else '';sign=1
   if verb in ("don't","doesn't"):
    sign=-1;parts=obj.split(' ',1);verb=parts[0];obj=parts[1] if len(parts)>1 else ''
   elif subject not in ('I','you'):verb=verb[:-1]
   if subject in ('everybody','nobody'):
    sign=-1 if subject=='nobody' else 1;subject='*'
   for s,v,o,t in facts:
    if (v,o)==(verb,obj) and t!=sign and (s==subject or s=='*' or subject=='*'):contradiction=True
   facts.append((subject,verb,obj,sign));continue
  if contradiction:answer='I am abroad.'
  elif body.startswith('who '):
   parts=body[4:].split(' ',1);verb=parts[0][:-1];obj=parts[1] if len(parts)>1 else '';subjects=[];generic=0
   for s,v,o,t in facts:
    if (v,o)!=(verb,obj):continue
    if s=='*':generic=t
    elif t==1 and s not in subjects:subjects.append(s)
   if generic:subject='everybody' if generic==1 else 'nobody';answer=subject+' '+activity(subject,verb,obj,1)+'.'
   elif subjects:
    subjects=list(map(swap,subjects));subject=subjects[0] if len(subjects)==1 else ', '.join(subjects[:-1])+' and '+subjects[-1];answer=subject+' '+activity(subjects[0],verb,obj,1,len(subjects)>1)+'.'
   else:answer="I don't know."
  elif body.startswith('what '):
   subject=body.split()[2];spoken=swap(subject);seen=set();phrases=[]
   for s,v,o,t in facts:
    if s in (subject,'*') and (v,o) not in seen:seen.add((v,o));phrases.append(activity(spoken,v,o,t))
   if not phrases:answer="I don't know."
   else:answer=spoken+' '+(phrases[0] if len(phrases)==1 else ', '.join(phrases[:-1])+', and '+phrases[-1])+'.'
  else:
   parts=body.split(' ',3);subject=parts[1];verb=parts[2];obj=parts[3] if len(parts)>3 else '';sign=0
   for s,v,o,t in facts:
    if s in (subject,'*') and (v,o)==(verb,obj):sign=t;break
   spoken=swap(subject);answer='maybe.' if not sign else ('yes, ' if sign==1 else 'no, ')+spoken+' '+activity(spoken,verb,obj,sign)+'.'
  output.extend([line,answer,''])
print('\n'.join(output))
