s=input().strip();pattern='WBWBWWBWBWBW'*3
for offset,name in zip((0,2,4,5,7,9,11),('Do','Re','Mi','Fa','So','La','Si')):
    if pattern[offset:offset+20]==s:print(name);break
