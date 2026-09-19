Xiao A and his family are visiting a park. The ticket prices are as follows:

![Ticket Prices](https://cdn.luogu.com.cn/upload/image_hosting/pc7vt43j.png?x-oss-process=image/resize,m_lfit,h_500,w_500)

Xiao A's family has $x$ adults and $y$ children. How much is the **minimum** amount of money needed to purchase the tickets?

## Input Format

A single line containing two numbers $x$ and $y$, representing the number of adults and children in Xiao A's family, respectively.

## Output Format

A single line containing one number, representing the **minimum** amount of money needed to purchase the tickets.

## Sample Input and Output

### Sample Input #1

```
1 1
```

### Sample Output #1

```
90
```

### Sample Input #2

```
2 1
```

### Sample Output #2

```
150
```

## Notes

### Explanation of Sample Input and Output #1

1 adult + 1 child can purchase a package ticket for one adult and one child, costing $90.

### Explanation of Sample Input and Output #2

2 adults + 1 child can purchase a package ticket for one adult and one child and an additional adult ticket, costing $90 + 60 = 150.

### Data Range and Constraints

For $20\%$ of the data, $y$ is guaranteed to be $0$;  
For another $20\%$ of the data, $x$ is guaranteed to be $0$;  
For another $20\%$ of the data, $x$ is guaranteed to be equal to $y$;  
For $100\%$ of the data, $0 \le x, y \le 100$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
