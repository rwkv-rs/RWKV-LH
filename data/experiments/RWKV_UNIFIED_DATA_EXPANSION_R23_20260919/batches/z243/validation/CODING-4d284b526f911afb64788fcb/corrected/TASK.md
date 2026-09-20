"Animal Crossing" is a game with a high degree of freedom where you can build houses, plant flowers and trees, and even catch bass on your own deserted island.

![](https://cdn.luogu.com.cn/upload/image_hosting/hd1w4hsq.png)

If a $(2k-1) \times (2k-1)$ square land satisfies that the outermost circle has a height of 1, the second circle has a height of 2, and so on, it is a pyramid with a height of k. The following figure shows examples of pyramids with heights from 1 to 4:

![](https://cdn.luogu.com.cn/upload/image_hosting/5gix9oyp.png)

Little A's island is a rectangle of size $n \times m$, and the height of each position is known. He wants to build a large pyramid. He has at most $k$ opportunities to reshape the terrain, each time choosing a coordinate to increase the height of that point by 1, but he cannot decrease the height. What is the maximum height of the pyramid he can complete?

## Input Format

Each test point consists of multiple sets of data.

The first line is an integer $T$, representing the number of data sets.

For each set of data, the first line contains three integers $n, m, k$, indicating the size of the island and the upper limit of the number of operations. The next $n$ lines and $m$ columns represent the initial heights, with each number separated by a space.

## Output Format

Output $T$ lines. For each line, output an integer representing the maximum height of the pyramid that can be completed for each set of data.

## Sample Input and Output

### Input Sample #1

```
3
5 5 10
1 1 1 1 1
1 2 1 1 1
1 1 1 1 1
1 1 1 2 1
1 1 1 1 1
5 5 5
1 1 1 1 1
1 2 1 1 1
1 1 1 1 1
1 1 1 2 1
1 1 1 1 1
1 1 1000000000
2
```

### Output Sample #1

```
3
2
0
```

## Notes/Hints

For all test data, $1 \le T \le 5$, $1 \le n, m \le 350$, $1 \le k \le 10^8$, and the initial heights are non-negative integers from 0 to 50.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
