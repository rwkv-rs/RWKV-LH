### Problem Translation
Many gas stations use plastic number tiles to display fuel prices. Among these tiles, $6$ and $9$, $2$ and $5$ can be considered interchangeable.

A gas station has run out of all number tiles, but the employees would like to continue to increase the fuel prices. They can change the order of the numbers or flip some of the numbers as described above. When increasing, the number of digits in both the integer part and the decimal part **must remain unchanged**. Given the original fuel price, your task is to provide the **minimum value** of the increased price or report no solution.

### Input Format
The input data consists of multiple lines, each containing one decimal number representing the original fuel price. **Specifically, when a line consists only of a decimal point, it indicates the end of input data.**

### Output Format
The output data consists of multiple lines, with each input line corresponding to one output line. If a solution exists, output one decimal number, representing the **minimum value** of the increased fuel price. If no solution exists, output the string `The price cannot be raised.`

### Data Constraints
For $100 \%$ of the data, the decimal number representing the original fuel price contains between $2$ and $30$ digits, and there is exactly $1$ decimal place. A leading zero will be present only when the original fuel price is less than $1$.

## Input and Output Examples

### Input Example #1

```
65.2
76.7
77.7
.
```

### Output Example #1

```
65.5
77.6
The price cannot be raised.
```
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
