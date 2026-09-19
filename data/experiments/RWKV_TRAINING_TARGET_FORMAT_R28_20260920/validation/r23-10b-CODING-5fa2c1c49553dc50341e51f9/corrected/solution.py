import sys
from collections import Counter
c=Counter(sys.stdin.read().strip());k=len(c);possible=k==4 or k==3 and sum(c.values())>=4 or k==2 and min(c.values())>=2
print('Yes' if possible else 'No')
