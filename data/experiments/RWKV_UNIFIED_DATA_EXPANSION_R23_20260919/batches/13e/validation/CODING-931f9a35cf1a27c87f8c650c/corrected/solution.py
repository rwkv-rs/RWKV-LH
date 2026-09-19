import sys
s=sys.stdin.read().strip();digits=[ord(c)-48 for c in s];prefix=sum(digits);carry=0;out=[]
for digit in reversed(digits):
 value=prefix+carry;out.append(str(value%10));carry=value//10;prefix-=digit
while carry:out.append(str(carry%10));carry//=10
print(''.join(reversed(out)))
