A company processes an alloy composed of iron, aluminum, and tin. Their process is straightforward. Initially, they import raw materials of iron-aluminum-tin alloys with different proportions of the components. Then, they take a certain amount of each raw material, melt it down, and mix it to produce a new alloy. The new alloy's proportions of iron, aluminum, and tin match the proportions required by the user.

Now, the user has provided \( n \) types of alloys they need, along with the proportions of iron, aluminum, and tin for each alloy. The company wishes to order the fewest types of raw materials and use these to produce all the types of alloys required by the user.

## Input Format

The first line contains two integers \( m \) and \( n \), representing the number of types of raw materials and the number of types of alloys required by the user, respectively.

From the second to the \( m+1 \)-th line, each line contains three real numbers \( a_i, b_i, c_i \), representing the proportions of iron, aluminum, and tin in one type of raw material.

From the \( m+2 \)-th to the \( m+n+1 \)-th line, each line contains three real numbers \( d_i, e_i, f_i \), representing the proportions of iron, aluminum, and tin in one type of alloy required by the user.

## Output Format

An integer representing the minimum number of types of raw materials needed. If there is no solution, output `-1`.

## Sample Input and Output

### Input Sample #1

```
10 10
0.1 0.2 0.7
0.2 0.3 0.5
0.3 0.4 0.3
0.4 0.5 0.1
0.5 0.1 0.4
0.6 0.2 0.2
0.7 0.3 0
0.8 0.1 0.1
0.9 0.1 0
1 0 0
0.1 0.2 0.7
0.2 0.3 0.5
0.3 0.4 0.3
0.4 0.5 0.1
0.5 0.1 0.4
0.6 0.2 0.2
0.7 0.3 0
0.8 0.1 0.1
0.9 0.1 0
1 0 0
```

### Output Sample #1

```
5
```

## Notes

### Data Size and Constraints

For all test cases, it is guaranteed that \( 1 \le m, n \le 500 \), \( 0 \le a_i, b_i, c_i, d_i, e_i, f_i \le 1 \), and \( a_i + b_i + c_i = 1 \), \( d_i + e_i + f_i = 1 \). The numbers are accurate to at most six decimal places.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
