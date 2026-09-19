Let S be the binary representation of an Integer. We define two functions a(i) and b(i) such that  
 a(i) = Number of occurrences of '1' at odd positions of S.  
 b(i) = Number of occurrences of '1' at even positions of S.  
 For example: for integer 19, S=10011.  
 so, a(19)=2 and b(19)=1

## Input Format

First line contains an integer T. T=Number of test cases. Then T lines follow  
 On each line, you will be given three integers M,N,K.

## Output Format

For each test case output a single integer R.  
 Where, R is the number of integers 'i' between M and N(both inclusive) such that absolute difference of a(i) and b(i) is equal to K.  
Answer of each each test case should be on separate line

## Sample Input and Output

### Sample Input #1

```
1
1 10 2
```

### Sample Output #1

```
2
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
