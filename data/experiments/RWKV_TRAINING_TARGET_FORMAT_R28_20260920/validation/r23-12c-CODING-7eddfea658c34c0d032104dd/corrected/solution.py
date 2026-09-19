import sys,re
lines=sys.stdin.read().splitlines();equations=[]
for line in lines:
 if not line.strip():continue
 left,right=line.replace(' ','').split('=');coeff={'x':0,'y':0}
 for raw,var in re.findall(r'([+-]?\d*)([xy])',left):coeff[var]+=(-1 if raw=='-' else 1 if raw in ('','+') else int(raw))
 equations.append((coeff['x'],coeff['y'],int(right)))
a,b,c=equations[0];d,e,f=equations[1];det=a*e-b*d;print((c*e-b*f)//det);print((a*f-c*d)//det)
