An Imp jumps on an infinite chessboard. Moves possible for the Imp are described by two pairs of integers: (a,b) and (c,d) - from square (x,y) the Imp can move to one of the squares: (x+a,y+b), (x-a,y-b), (x+c,y+d), (x-c,y-d). We want to know for which square different from (0,0) to which the Imp can jump from (0,0) (possibly in many moves) the value |x|+|y| is the lowest.

  
###  Task 

Write a program which

- reads from standard input two pairs (a,b) and (c,d) of integers, different from (0,0), describing moves of the Imp,
- determines a pair of integers (x,y) different from (0,0), for which the Imp can jump (possibly in many moves) from square (0,0) to square (x,y) and for which the value |x|+|y| is the lowest.
- writes out to standard output the value |x|+|y|.

## Input Format

Ten test cases. Each test consists of four numbers a,b,c,d in one line, separated by spaces.   
-100000 <= a, b, c, d <= 100000

## Output Format

For every test case your program should write a single line with a number equal the lowest possible value |x|+|y|.

## Sample Input and Output

### Sample Input #1

```
13 4 17 5
[and 9 test cases more]
```

### Sample Output #1

```
2
[and 9 answers more]
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
