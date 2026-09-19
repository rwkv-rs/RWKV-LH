import sys,itertools
n=int(sys.stdin.buffer.read());powers=[d**n for d in range(10)];count=0
for digits in itertools.combinations_with_replacement(range(10),n):
 value=sum(powers[d] for d in digits)
 if value>0 and len(str(value))==n and tuple(sorted(map(int,str(value))))==digits:count+=1
print(count)
