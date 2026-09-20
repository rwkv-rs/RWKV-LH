import sys
out=[]
for line in sys.stdin.buffer:
 if line.startswith(b'#'):break
 if line.endswith(b'\n'):line=line[:-1]
 if line.endswith(b'\r'):line=line[:-1]
 value=0
 for b in line:value=(value*256+b)%34943
 crc=(-value*65536)%34943;out.append(f'{crc>>8:02X} {crc&255:02X}')
print('\n'.join(out))
