When two resistors are connected in series, their equivalent resistance is the sum of their resistances. For example, if two resistors with resistance values of $100$ Ohms and $200$ Ohms are connected in series, the equivalent resistance will be $300$ Ohms. If more resistors are connected in series, their total resistance will be the sum of the resistances of all individual resistors.

Resistors can also be connected in parallel: for three resistors connected in parallel, with resistance values of $100$ Ohms, $150$ Ohms, and $300$ Ohms respectively, the equivalent resistance will be:
$$\frac{1}{\frac{1}{100} + \frac{1}{150} + \frac{1}{300}} \text{ Ohms. }$$

In this problem, you will be given multiple sets of data about resistor values and their connection methods. Each end of a resistor can be a connection point, and these connection points are uniquely identified by positive integers called labels. Each resistor is specified by the labels of its two connection points and a real number representing its resistance value. For example, the input: ```1 2 100``` specifies a resistor with a resistance of $100$ Ohms between connection points $1$ and $2$. Two series resistors can be specified as follows:
```
1 2 100
2 3 200
```
Given the resistance values and their connection methods, you can determine the equivalent resistance between any two connection points in the resistor network by applying the rules mentioned above to calculate the equivalent resistance. In certain special cases, the method might not be able to determine the equivalent resistance value; however, this problem's test data does not contain such cases.

**Note:**
- In the test data, some resistors may not affect the equivalent resistance between the specified two connection points. For instance, in the last set of data in the sample input, the resistor between connection points $1$ and $2$ is not used. A resistor only affects the total equivalent resistance if a current passes through it.
  
- The test data will not contain situations where both ends of a resistor are connected to the same connection point; in other words, the labels of the connection points at both ends of a resistor will not be the same.
  
### Input
The input contains multiple sets of test data. Each set of test data begins with a line containing three integers $N$, $A$, and $B$. $A$ and $B$ denote the labels of the two connection points for which you need to calculate the equivalent resistance. $N$ is the total number of resistors, which does not exceed $30$. $N$, $A$, and $B$ all being $0$ indicates the end of the test data and should not be processed. Following the first line of each set of test data, there are $N$ lines, each describing a resistor by specifying the labels of its two connection points and its resistance value as a real number.

### Output
For each set of test data, first output the test data set number (starting from $1$), then output its equivalent resistance, accurate to two decimal places.

## Sample Input and Output

### Sample Input #1

```
2 1 3
1 2 100
2 3 200
2 1 2
1 2 100
1 2 150
6 1 6
1 2 500
1 3 15
3 4 40
3 5 100
4 6 60
5 6 50
0 0 0
```

### Sample Output #1

```
Case 1: 300.00 Ohms
Case 2: 60.00 Ohms
Case 3: 75.00 Ohms
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
