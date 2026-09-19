Country C has a comprehensive expressway network represented as a tree.

There are \( n \) cities in Country C, connected by a total of \( n-1 \) expressways. Except for the capital, which is the city numbered 1, each city has a local passenger transport company that can dispatch vehicles to anywhere in the country. You can consider this as a tree with city 1 as the root. The distance between two cities is defined as the length of the simple path between them.

Suppose someone wants to travel from city \( i \) to city \( j \) which is \( D \) units away. The cost of the journey will be \( P_i \times D + Q_i \) yuan. Since the further a city is from the capital, the less regulated it is, the \( P_i \) value of the transport company increases with distance from the capital. If city \( i \) is an ancestor of city \( j \), then it is guaranteed that \( P_i \leq P_j \).

Xiao T has been appointed as an investigator by the National Bureau of Statistics. He needs to conduct an investigation on the current expressway network to understand the cost of traveling from every other city to the capital city 1.

Given the possibility of multiple transfers (or no transfers) to reach the capital, calculating this manually is quite complex. Xiao T is very lazy, so he asks you to write a program to solve this problem.

## Input Format

The first line contains an integer \( n \), representing the number of cities.

From the second to the \( n \)-th line, each line describes a city other than the capital. Each line contains four integers \( F_i, S_i, P_i, Q_i \), representing the parent city of city \( i \), the length of the expressway to the parent city, and the two parameters for the travel cost.

## Output Format

The output contains \( n-1 \) lines, each containing a single integer.

The \( i \)-th line represents the minimum travel cost from city \( i+1 \) to the capital.

## Sample Input and Output

### Input Sample #1

```
6
1 9 3 0
1 17 1 9
1 1 1 6
4 13 2 15
4 9 2 4
```

### Output Sample #1

```
27
26
7
43
24
```

## Notes

### Data Size and Constraints

- For the first 40% of the data, \( n \leq 1000 \).
- For another 20% of the data, \( F_i = i-1 \).
- For all data, \( 1 \leq n \leq 10^6 \), \( 0 \leq P_i, Q_i < 2^{31} \), and the result will not exceed \( 2^{63}-1 \).

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
