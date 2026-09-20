import sys
lines=sys.stdin.read().splitlines();departments=int(lines[0]);department='';records=[]
for line in lines[1:]:
 if not line.strip():continue
 if ',' not in line:department=line;continue
 fields=line.split(',');records.append((fields[2],fields,department))
records.sort(key=lambda r:r[0]);out=[]
for _,f,department in records:
 title,first,last,address,home,work,box=f;out.extend(['-'*40,f'{title} {first} {last}',address,'Department: '+department,'Home Phone: '+home,'Work Phone: '+work,'Campus Box: '+box])
print('\n'.join(out))
