import sys,math
A,B=map(int,sys.stdin.buffer.read().split());counts=[0]*10;factorial=[math.factorial(i) for i in range(19)];answer=0

def rank(bound,length,ways):
 digits=str(bound)
 if len(digits)<length:return 0
 if len(digits)>length:return ways
 total=0;taken=[];left=length
 for ch in digits:
  d=ord(ch)-48;less=sum(counts[1:d]);total+=ways*less//left
  if d==0 or counts[d]==0:break
  ways=ways*counts[d]//left;counts[d]-=1;taken.append(d);left-=1
 else:total+=1
 for d in taken:counts[d]+=1
 return total

def visit(start,minimum,product,length,denominator):
 global answer
 for digit in range(start,10):
  number=minimum*10+digit;prod=product*digit
  if number*prod>B:break
  counts[digit]+=1;n=length+1;den=denominator*counts[digit];ways=factorial[n]//den
  answer+=rank(B//prod,n,ways)-rank((A-1)//prod,n,ways)
  if n<18:visit(digit,number,prod,n,den)
  counts[digit]-=1
visit(1,0,1,0,1)
print(answer)
