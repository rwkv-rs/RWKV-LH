import sys
v=list(map(int,sys.stdin.buffer.read().split()));out=[]
for day in v[1:]:
 if day>=2299161:
  a=day+32044;b=(4*a+3)//146097;c=a-146097*b//4;d=(4*c+3)//1461;e=c-1461*d//4;m=(5*e+2)//153
  year=100*b+d-4800+m//10
 else:
  c=day+32082;d=(4*c+3)//1461;e=c-1461*d//4;m=(5*e+2)//153;year=d-4800+m//10
 date=e-(153*m+2)//5+1;month=m+3-12*(m//10)
 out.append(f'{date} {month} {year}' if year>0 else f'{date} {month} {1-year} BC')
print('\n'.join(out))
