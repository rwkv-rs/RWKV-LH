import sys
v=sys.stdin.buffer.read().split();q=int(v[1]);sys.stdout.write('\n'.join('X' if (int(x)-1).bit_count()%2==0 else 'Z' for x in v[2:2+q]))
