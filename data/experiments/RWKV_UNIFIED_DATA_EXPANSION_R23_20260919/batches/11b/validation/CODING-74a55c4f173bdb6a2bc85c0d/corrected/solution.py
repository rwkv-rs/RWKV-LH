import sys,re
sys.setrecursionlimit(1000000);tokens=re.findall(r'-?\d+|[()]',sys.stdin.read());at=0;out=[]
def tree(total,target):
 global at
 at+=1
 if tokens[at]==')':at+=1;return False,False
 value=int(tokens[at]);at+=1;left,yes_left=tree(total+value,target);right,yes_right=tree(total+value,target);at+=1
 return True,yes_left or yes_right or not left and not right and total+value==target
while at<len(tokens):
 target=int(tokens[at]);at+=1;exists,found=tree(0,target);out.append('yes' if found else 'no')
print('\n'.join(out))
