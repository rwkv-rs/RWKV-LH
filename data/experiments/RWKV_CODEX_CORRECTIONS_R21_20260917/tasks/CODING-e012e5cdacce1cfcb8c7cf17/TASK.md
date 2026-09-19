The inevitable day has arrived, and Xiao F is staring at the night sky.

The sky is empty, devoid of any stars—likely due to the unyielding clouds overhead.

The clouds of worry in Xiao F's heart will remain there; there's no chance to change anything anyway.

Xiao C brings a long string of star-shaped light bulbs, pretending they are stars, to cheer up Xiao F. However, Xiao F, with his obsessive-compulsive disorder, notices that out of the total $n$ light bulbs, $k$ are not lit. Xiao F decides to work with Xiao C to light up all the bulbs.

Unfortunately, Xiao F is clumsy and can only invert the state of a continuous segment of bulbs—turning off lit bulbs and turning on unlit ones. After experimenting, Xiao F finds that he can invert the state of bulbs in $m$ different lengths of segments.

Xiao C and Xiao F eventually spend an incredibly long time lighting up all the bulbs. They wonder if they were foolish and thus seek your help to calculate the minimum number of operations required to light up the entire string of bulbs under the best scenario.

## Input Format

Read data from standard input.

The first line contains three positive integers $n, k, m$.

The second line contains $k$ positive integers, where the $i$-th number represents the position $a_i$ of the $i$-th unlit bulb.

The third line contains $m$ positive integers, where the $i$-th number represents the length $b_i$ of the $i$-th operation.

It is guaranteed that all $b_i$ are distinct; for $1 \le i < k$, $a_i < a_{i+1}$; and that the input data has a solution.

## Output Format

Output to standard output.

Output a single non-negative integer, representing the minimum number of operations.

## Sample Input and Output

### Input Example #1

```
5 2 2 
1 5 
3 4
```

### Output Example #1

```
2
```

## Notes/Hints

[Sample 1 Explanation]

![Explanation Image](https://cdn.luogu.com.cn/upload/pic/9814.png)

[Data Range and Constraints]

Subtasks provide characteristics of some test data. If you encounter difficulties solving the problem, you can attempt to solve only part of the test data.

The scale and characteristics of the data for each test point are as follows:

![Data Range Image](https://cdn.luogu.com.cn/upload/pic/9815.png)

Special Property: The answer is guaranteed to be less than 4.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
