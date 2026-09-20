import sys,math
C,Hr,Hb,Wr,Wb=map(int,sys.stdin.buffer.read().split())
if Hr*Wb<Hb*Wr:Hr,Hb=Hb,Hr;Wr,Wb=Wb,Wr
answer=0
if Wr<=math.isqrt(C):
 for blue in range(min(C//Wb,Wr//math.gcd(Wr,Wb)-1)+1):answer=max(answer,blue*Hb+(C-blue*Wb)//Wr*Hr)
else:
 for red in range(C//Wr+1):answer=max(answer,red*Hr+(C-red*Wr)//Wb*Hb)
print(answer)
