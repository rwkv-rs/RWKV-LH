Little C's rabbits are not snow-white but rather colorful. Each rabbit has a color, and different rabbits may share the same color. Little C arranges her $n$ rabbits, numbered from 1 to $n$, in a long row to feed them carrots. After the arrangement, the color of the $i$-th rabbit is $a_i$.

As the saying goes, "Different strokes for different folks." Little C finds that rabbits of different colors may have different preferences for carrots. For example, silver rabbits love golden carrots the most, golden rabbits prefer carrot leaves, and green rabbits like slightly sour carrots... To meet the rabbits' demands, Little C is quite troubled. Therefore, to feed the carrots more accurately, Little C wants to know how many rabbits of color $c_j$ are in the interval $[l_j, r_j]$.

However, because Little C's rabbits are very active and do not like to stay in a fixed position, and Little C is also adjusting their positions based on the information she knows, sometimes the two rabbits numbered $x_j$ and $x_j+1$ will swap places. Little C is stumped by these series of troubles. Can you help her?

## Input Format

Read data from standard input. The first line contains two positive integers $n$ and $m$.

The second line contains $n$ positive integers, where the $i$-th number represents the color $a_i$ of the $i$-th rabbit.

The next $m$ lines each contain one of the following two types of operations:

- "1 $l_j$ $r_j$ $c_j$": Query how many rabbits of color $c_j$ are in the interval $[l_j, r_j]$.
- "2 $x_j$": The rabbits numbered $x_j$ and $x_j+1$ swap places.

## Output Format

Output to standard output.

For each operation of type 1, output a single positive integer on a new line, which is your answer to that query.

## Sample Input and Output

### Input Sample #1

```
6 5 
1 2 3 2 3 3  
1 1 3 2 
1 4 6 3  
2 3 
1 1 3 2  
1 4 6 3
```

### Output Sample #1

```
1 
2 
2 
3 
```

## Notes

**Sample 1 Explanation**

The first two and the last two operations of type 1 are the same; after the third operation of type 2, the rabbits numbered 3 and 4 swap places, and the sequence becomes 1 2 2 3 3 3.

**Data Range and Constraints**

Subtasks will provide characteristics of some test data. If you encounter difficulties in solving the problem, you can try to solve only part of the test data. For all test cases, it holds that $1 \le l_j < r_j \le n, 1 \le x_j < n$. The scale and characteristics of the data for each test point are as follows:

![Data Range and Constraints](https://cdn.luogu.com.cn/upload/pic/9808.png)

Special Property 1: For all type 1 operations, it is guaranteed that $|r_j - l_j| \le 20$ or $|r_j - l_j| \le n - 20$.

Special Property 2: It is guaranteed that no two rabbits have the same color.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
