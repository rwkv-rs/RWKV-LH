from functools import lru_cache
@lru_cache(None)
def serve(x,y,s):
 if x+y==0:return(0,0)
 if s==0:
  if x:return respond(x-1,y,1)
  return serve(x,y,1)
 if y:return respond(x,y-1,0)
 return serve(x,y,0)
@lru_cache(None)
def respond(x,y,t):
 w=1-t;a=list(serve(x,y,w));a[w]+=1;opts=[tuple(a)]
 if (x,y)[t]:opts.append(respond(x-(t==0),y-(t==1),1-t))
 return max(opts,key=lambda a:(a[t],-a[1-t]))
for x in range(1,11):print(x,[serve(x,y,0) for y in range(1,8)])
