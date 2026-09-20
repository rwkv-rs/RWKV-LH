import sys,math
out=[]
for word in sys.stdin.buffer.read().split():
 bits=word.decode();raw=int(bits,2)
 if raw&32767==0:value=0.0
 else:value=math.ldexp(1+(raw&255)/256,((raw>>8)&127)-63)*(-1 if raw>>15 else 1)
 mantissa,exponent=f'{value: .6e}'.split('e');exp=int(exponent);out.append(mantissa+'e'+('+' if exp>=0 else '-')+str(abs(exp)).zfill(3))
print('\n'.join(out))
