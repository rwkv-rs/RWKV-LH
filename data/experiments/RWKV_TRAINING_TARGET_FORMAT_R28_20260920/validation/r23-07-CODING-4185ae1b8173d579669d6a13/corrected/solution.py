import sys,datetime
x,y=map(int,sys.stdin.read().split());print(sum(datetime.date(year,11,11).weekday()>=5 for year in range(x,y+1)))
