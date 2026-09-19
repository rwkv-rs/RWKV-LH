Since the above two problems are not available on Luogu, this problem has been created.

## Problem Description

Calculate the number of isomers for **olefins (ethylene homologues)** with the chemical formula $\text{C}_n \text{H}_{2n}$.

Stereoisomerism and cis-trans isomerism are not considered in this problem.

The answer should be taken modulo $998244353$.

## Input Format

A positive integer $n$.

## Output Format

A total of $n-1$ lines, each containing the answer for the number of carbon atoms ranging from $2$ to $n$.

## Sample Input and Output

### Sample Input #1

```
5
```

### Sample Output #1

```
1
1
3
5
```

## Notes

### Sample 1 Explanation

+ $n=2$: Ethylene.
+ $n=3$: Propene.
+ $n=4$: 1-Butene; 2-Butene; 2-Methyl-1-propene.
+ $n=5$: 1-Pentene; 2-Pentene; 2-Methyl-1-butene; 3-Methyl-1-butene; 2-Methyl-2-butene.

### Data Range and Constraints

For $100\%$ of the data, it is guaranteed that $1 \leq n \leq 100000$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
