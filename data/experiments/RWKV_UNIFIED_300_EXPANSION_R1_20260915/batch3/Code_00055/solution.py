import sys
from functools import lru_cache
a=list(map(int,sys.stdin.buffer.read().split()));n,x=a[:2];coins=a[2:]
@lru_cache(None)
def f(i,amount):
    if i==n-1:return 1
    next_coin=coins[i+1];remainder=amount%next_coin
    if remainder==0:return f(i+1,amount)
    return f(i+1,amount-remainder)+f(i+1,amount-remainder+next_coin)
print(f(0,x))
