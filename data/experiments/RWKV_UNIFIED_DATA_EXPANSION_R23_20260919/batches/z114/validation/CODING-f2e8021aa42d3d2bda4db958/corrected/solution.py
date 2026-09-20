import sys
binary=sys.stdin.read().strip();parts=binary.split('.');whole=parts[0];whole='0'*((-len(whole))%3)+whole;integer=''.join(str(int(whole[i:i+3],2)) for i in range(0,len(whole),3)).lstrip('0') or '0';octal=integer
if len(parts)==2:
 fraction=parts[1];fraction+='0'*((-len(fraction))%3);octal+='.'+''.join(str(int(fraction[i:i+3],2)) for i in range(0,len(fraction),3))
letters=''.join(' ' if c in '0.' else chr(ord('A')+int(c)-1) for c in octal)
print(octal+' '+letters)
