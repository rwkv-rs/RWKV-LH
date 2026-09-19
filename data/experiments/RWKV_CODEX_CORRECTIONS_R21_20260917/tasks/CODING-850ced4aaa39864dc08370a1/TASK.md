Chain & Co. specializes in producing infinitely strong chains. Because of their high quality products, they are quickly gaining market share. This leads to new challenges, some of which they could have never imagined before. Like, for example, automatic verification of link endurance with a computer program, which you are supposed to write.

The company produces links of equal size. Each link is an infinitely thin square frame in three dimensions (made of four infinitely thin segments).

During tests, all links are axis-aligned and placed so that no two frames touch. To make a proper strength test, two sets of links A and B are forged so that every link of A is inseparable from every link of B (being inseparable means that they cannot be moved apart without breaking one of them).

You stumble upon some links (axis-aligned, pairwise disjoint). Are they in proper testing position? In other words, can they be divided into two non-empty sets A and B with the desired property?

Axis-aligned means that all segments are parallel to either X, Y, or Z axis.

## Input Format

The first line of input contains the number of test cases T. The descriptions of the test cases follow:

The description of each test case starts with an empty line. The next line contains an integer n, \(1 \le n \le 10^6\) - the number of links in the chain. Each of the next n lines contains 6 space-separated integers \(x_i, y_i, z_i, x_i', y_i', z_i'\), all between \(-10^9\) and \(10^9\) - the coordinates of two opposite corners of the i-th link.

## Output Format

For each test case, print a single line containing the word YES if the set is in proper testing position, or NO otherwise.

## Sample Input and Output

### Input Sample #1

```
3

2
0 0 0 0 10 10
-5 5 15 5 5 25

5
0 0 0 0 10 10
-5 5 6 5 5 16
-5 5 -6 5 5 4
-5 6 5 5 16 5
-5 -6 5 5 4 5

3
0 0 0 3 0 -3
1 -1 -1 1 2 -4
-1 -2 -2 2 1 -2
```

### Output Sample #1

```
NO
YES
YES
```

## Notes/Hints

Time limit: 10 s, Memory limit: 128 MB.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
