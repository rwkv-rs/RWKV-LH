The Worldwide Network (WWN) is a leading company in operating large-scale telecommunications networks. WWN plans to establish a new network in Borduria, and you need to assist WWN in determining how to set up its network at the lowest possible total cost. There are several local companies operating small networks (referred to as subnets) that partially cover the n largest cities of Borduria. WWN wants to build a network that connects all n cities. To achieve this, it can either construct a network from scratch between the cities or purchase one or more subnets from local companies. Your task is to help WWN decide which existing networks to buy and which edges to construct to minimize the total cost.

1. The coordinates (in two-dimensional space) of all n cities are given.

2. There are q subnets. If q≥1, the connecting cities in each subnet are provided (the shape of the connection does not matter).

3. A subnet can only be purchased as a whole and cannot be divided.

4. To connect two cities that are not directly connected, an edge must be constructed. The cost of constructing this edge is the square of the Euclidean distance between the cities.

Your task is to determine which existing networks to purchase and which edges to construct such that the total cost is minimized.

## Input Format

The first line of the input file contains an integer T, indicating the number of test cases. A blank line follows. Each test case is separated by a blank line.

For each test case:

The first line contains two integers, the total number of cities n and the number of subnets q, where 1≤n≤1000 and 0≤q≤8. Cities are numbered from 1 to n.

The next q lines each contain multiple integers. The first integer denotes the number of cities m in that subnet, the second integer represents the cost of purchasing this subnet (which does not exceed 2*10^6), and the remaining m integers indicate the cities contained in this subnet.

The following n lines each contain two integers, representing the coordinates of the ith city (coordinates range from 0 to 3000).

## Output Format

For each test case, output a line with the total cost of constructing the network. Separate outputs for different test cases with a blank line.

## Sample Input

```
1
7 3
2 4 1 2
3 3 3 6 7
3 9 2 4 5
0 2
4 0
2 0
4 2
1 3
0 5
4 4

```

## Sample Output

```
17

```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
