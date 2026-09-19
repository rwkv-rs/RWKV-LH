import sys
v=sys.stdin.read().split();n=int(v[0]);months='pop no zip zotz tzec xul yoxkin mol chen yax zac ceh mac kankin muan pax koyab cumhu uayet'.split();names='imix ik akbal kan chicchan cimi manik lamat muluk ok chuen eb ben ix mem cib caban eznab canac ahau'.split();out=[str(n)]
for i in range(n):
 day,month,year=v[1+3*i:4+3*i];total=int(year)*365+months.index(month)*20+int(day.rstrip('.'));out.append(str(total%13+1)+' '+names[total%20]+' '+str(total//260))
print('\n'.join(out))
