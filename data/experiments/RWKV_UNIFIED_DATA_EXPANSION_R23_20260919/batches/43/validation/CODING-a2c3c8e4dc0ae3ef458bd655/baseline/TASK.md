You are initially given an empty array of Size **N** (<=100000). (i.e. each element is 0).

Given 2 <= **R** <=10 $ ^{9} $ .

Now you are given 3 types of query:

1. "0 St i1 i2": means add (St, St\*R , St\*R^2 ,....) GP from i1 to i2 respectively. (Means add the GP with start term St and common ratio R in the series begining from i1 and ending at i2.)
2. "1 i j": means find the sum of values of the array from index **i** to index **j** with modulo 1000000007.
3. "2 i": resets the **i**-th index array to 0.

## Input Format

First Line contains **N** **R** **Q**.  
 Then Follows **Q** lines, each line can be of any 3 types described above.

## Output Format

Output only second type of Query.

## Sample Input and Output

### Sample Input #1

```
\n2 2 3\n0 2 1 2\n1 1 2\n1 2 2\n\n
```

### Sample Output #1

```
\n6\n4
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
