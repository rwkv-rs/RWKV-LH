import sys,re
s=sys.stdin.read().strip();out=[]
for match in re.finditer(r'([+-]?)([0-9]+)',s):
 sign,digits=match.groups()
 if sign!='-' or len(digits)==1:out.append(sign+digits);continue
 out.append('-'+digits[0]);rest=digits[1:]
 while rest.startswith('0'):out.append('+0');rest=rest[1:]
 if rest:out.append('+'+rest)
print(''.join(out))
