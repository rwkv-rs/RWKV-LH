import sys
pairs={'A':'A','E':'3','H':'H','I':'I','J':'L','L':'J','M':'M','O':'O','S':'2','T':'T','U':'U','V':'V','W':'W','X':'X','Y':'Y','Z':'5','1':'1','2':'S','3':'E','5':'Z','8':'8'};out=[]
for s in sys.stdin.read().split():
 palindrome=s==s[::-1];mirror=all(pairs.get(a)==b for a,b in zip(s,s[::-1]));label=('a mirrored palindrome' if palindrome else 'a mirrored string') if mirror else ('a regular palindrome' if palindrome else 'not a palindrome');out.append(s+' -- is '+label+'.')
print('\n\n'.join(out)+'\n')
