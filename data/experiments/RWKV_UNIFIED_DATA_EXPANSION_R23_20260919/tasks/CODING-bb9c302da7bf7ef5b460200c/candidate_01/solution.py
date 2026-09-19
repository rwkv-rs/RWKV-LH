import sys
from collections import Counter
c=Counter(sys.stdin.read().strip());print(max(0,min((c['n']-1)//2,c['i'],c['e']//3,c['t'])))
