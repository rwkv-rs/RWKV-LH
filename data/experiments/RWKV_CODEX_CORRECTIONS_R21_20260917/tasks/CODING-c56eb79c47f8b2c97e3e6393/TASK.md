There are $n$ types of food and $m$ people. Your task is to buy some food in such a way that no person feels overstuffed, and under this premise, you aim to spend as much money as possible. For each person $i$, each type of food $j$ has a coefficient $a_{ij}$, which indicates the joy value this person gains per unit of that food. Each person $i$ also has a maximum joy value $b_i$, which signifies that if the total joy value from the food surpasses $b_i$, this person will feel overstuffed.

**Input Format**

The input contains multiple datasets. Each dataset's first line consists of two integers $n$ and $m$, and the second line includes $n$ real numbers representing the unit price of each type of food. The following $m$ lines each contain $n+1$ real numbers, with the first $n$ real numbers representing the coefficients $a_{i1}, a_{i2}, ..., a_{in}$, and the last real number representing $b_i$. The input ends at EOF.

**Output Format**

For each dataset, output the maximum amount of money spent, rounded up to the nearest integer. The specific format is shown in the example.

**Data Range**

$3 \leq n, m \leq 20$.

## Input and Output Example

### Input Example #1

```
3 3
1 0.67 1.67
1 2 1 430
3 0 2 460
1 4 0 420
```

### Output Example #1

```
Nasa can spend 1354 taka.
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
