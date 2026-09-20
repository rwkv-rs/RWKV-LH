import sys
color=sys.stdin.readline().strip();value=int(color[1:],16);print(f'#{value^0xFFFFFF:06X}')
