**Problem Source**:  
University of Ulm Local Contest 1998, ZOJ1952, ZOJ2263, uva544

**Problem Description**  
Big Johnsson Transport Car Manufacturing Company specializes in the production of large vehicles. Their latest model, the Godzilla V12, has such a large carrying capacity that the weight it can transport is never limited by the vehicle itself, but rather by the weight restrictions of the roads it travels.  
Given a starting city and a destination city, your task is to compute the maximum weight that the Godzilla V12 can transport from the starting city to the destination city without exceeding the weight limits of the roads on the path.

**Input**  
The input file contains multiple test cases. Each test case begins with a line containing two integers: the number of cities `n` (2≤n≤200), and the number of roads `r` that make up the road network (1≤r≤19900).  
The next `r` lines each describe a road that directly connects two cities, in the format: the names of the two connected cities, followed by the weight limit of the road. City names will not exceed 30 characters and will not contain spaces. The weight limit is an integer between 0 and 10000. Roads are bidirectional.  
The last line of each test case consists of the names of two cities: the starting city and the destination city.  
The final line of the input file consists of two 0s, representing the end of the input.

**Output**  
For each test case, output 3 lines:

- The first line is formatted as: `"Scenario #x"`, where `x` is the test case number.
- The second line is: `"y tons"`, where `y` is the maximum possible load weight.
- The third line is a blank line.

Provided by @above is rbq

## Sample Input and Output

### Sample Input #1

```
4 3
Karlsruhe Stuttgart 100
Stuttgart Ulm 80
Ulm Muenchen 120
Karlsruhe Muenchen
5 5
Karlsruhe Stuttgart 100
Stuttgart Ulm 80
Ulm Muenchen 120
Karlsruhe Hamburg 220
Hamburg Muenchen 170
Muenchen Karlsruhe
0 0
```

### Sample Output #1

```
Scenario #1
80 tons

Scenario #2
170 tons
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
