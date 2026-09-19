import sys
v=list(map(int,sys.stdin.buffer.read().split()));required=sum(x<<i for i,x in enumerate(v));full=(1<<16)-1;left=sum(1<<(4*i) for i in range(4));right=left<<3;edge=left|right|15|(15<<12)
def spread(bits):return ((bits&~left)>>1)|((bits&~right)<<1)|(bits<<4)|(bits>>4)
def fill(seed,allowed):
 seen=seed
 while True:
  new=seen|(spread(seen)&allowed)
  if new==seen:return seen
  seen=new
answer=0;optional=full^required;part=optional
while True:
 mask=required|part
 if fill(mask&-mask,mask)==mask:
  outside=full^mask
  if fill(outside&edge,outside)==outside:answer+=1
 if part==0:break
 part=(part-1)&optional
print(answer)
