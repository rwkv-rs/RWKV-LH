import sys
v=list(map(int,sys.stdin.read().split()));answers={1:3,2:9};same=3;different=6
for n in range(3,31):same,different=same+different,2*same+different;answers[n]=same+different
print('\n'.join(str(answers[n]) for n in v[1:1+v[0]]))
