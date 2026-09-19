import sys
lines=sys.stdin.read().splitlines();at=0;books=[]
while lines[at]!='END':
 title,author=lines[at].rsplit(' by ',1);books.append((author,title));at+=1
books.sort();titles=[title for author,title in books];index={title:i for i,title in enumerate(titles)};present=set(range(len(books)));returned=set();at+=1;out=[]
for line in lines[at:]:
 if line=='END':break
 if line.startswith('BORROW '):present.remove(index[line[7:]])
 elif line.startswith('RETURN '):returned.add(index[line[7:]])
 elif line=='SHELVE':
  previous=None
  for i,title in enumerate(titles):
   if i in returned:
    out.append('Put '+title+(' first' if previous is None else ' after '+titles[previous]));present.add(i)
   if i in present:previous=i
  returned.clear();out.append('END')
print('\n'.join(out))
