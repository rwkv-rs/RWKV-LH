import sys
seen=set();parts=[]
for line in sys.stdin:
 s=line.rstrip('\r\n')
 if s=='0':break
 if s not in seen:seen.add(s);parts.append(s)
print(''.join(parts))
