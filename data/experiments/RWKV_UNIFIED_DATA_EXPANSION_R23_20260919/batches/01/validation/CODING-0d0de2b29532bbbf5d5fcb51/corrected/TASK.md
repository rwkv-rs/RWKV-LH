**Problem Description**  
Given a square cake of size $1000 \times 1000$, determine how many pieces the cake is divided into after it has been cut a certain number of times. Assume:  
1. No more than $8$ cuts are made;
2. After each cut, the length of each cake piece is not less than $1$;
3. The coordinates of the four corners of the cake are $(0, 0), (0, 1000), (1000, 1000), (1000, 0)$;
4. Each cut line intersects the cake's edge at exactly two points.

**Input Format**  
The first line of the input is an integer $M$, followed by a blank line, and then $M$ sets of test data. There is a blank line between each pair of test data sets.  
Each set of test data begins with an integer indicating the number of cuts, followed by the details of each cut line. Each cut line is defined by $4$ integers, representing the coordinates where the cut line intersects the cake's edges.

**Output Format**  
For each set of test data, output a single line indicating the number of cake pieces after the cuts. There should be a blank line between the answers for each pair of test data sets.

## Input and Output Example

### Input Sample #1

```
1
3
0 0 1000 1000
500 0 500 1000
0 500 1000 500
```

### Output Sample #1

```
6
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
