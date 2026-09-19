import sys
if hasattr(sys,'set_int_max_str_digits'):sys.set_int_max_str_digits(0)
n=int(sys.stdin.read());q,r=divmod(n,3)
value=3**q if r==0 else 4*3**(q-1) if r==1 else 2*3**q
s=str(value);print(len(s));print(s[:100])
