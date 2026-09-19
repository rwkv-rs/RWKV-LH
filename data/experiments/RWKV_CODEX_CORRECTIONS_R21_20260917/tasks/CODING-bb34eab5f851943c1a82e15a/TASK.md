Combinatory logic can be considered as one of the computational models that allows expressing any computable function as a composition of functions from a small finite basis. In this problem, we consider a restricted variant of the BCKW basis, BCKI.

A combinator expression in the BCKI basis is a string corresponding to the following grammar:

```plain
⟨Expression⟩ ::= ⟨Expression⟩ ⟨Term⟩ | ⟨Term⟩
⟨Term⟩ ::= ‘(’⟨Expression⟩‘)’ | ‘B’ | ‘C’ | ‘K’ | ‘I’
```

As seen from the grammar, the expression is a tree of applications where leaves are combinators $B, C, K$, and $I$. The application is left-associative. For example, $BIC$ is equivalent to $(BI)C$, but not to $B(IC)$.

For explanation purposes, we will use lowercase English letters $(a \cdots z)$ to represent sub-expressions. These lowercase letters will not appear in real data. For example, $BIC$ can be represented by $BxC$ (i.e., $B\underbrace{I}_{x}C)$, $x(\underbrace{BIC}_{x})$, $xy(\underbrace{BI}_{x}\underbrace{C}_{y})$, $Bxy (B\underbrace{I}_{x}\underbrace{C}_{y})$, but not by $Bx$.

In expression $pq$, we apply $p$ to $q$. We can intuit that $p$ is a function and $q$ is its parameter. However, the evaluation process is quite different from traditional computation—instead of passing values over a fixed expression tree, we evaluate by altering that tree so that the result is also some combinator expression.

To evaluate an expression, we need to select some sub-expression corresponding to one of the patterns specified in the table below—that is, there should exist such $x$ (and maybe $y$ and $z$) that the pattern from the table becomes equal to the sub-expression. Then we need to replace the sub-expression with the reduction result from the table.

| Pattern | Reduction result | Description |
| :-----: | :--------------: | :---------------------------------------------: |
| $Bxyz$  |     $x(yz)$      | Composition function (Zusammensetzungsfunktion) |
| $Cxyz$  |     $(xz)y$      | Exchange function (Vertauschungsfunktion) |
|  $Kxy$  |       $x$        | Constant function (Konstanzfunktion) |
|  $Ix$   |       $x$        | Identity function (Identitätsfunktion) |

After the replacement, we must repeat the process until there remain no suitable sub-expressions. This final expression is the normal form of the original one. For example, in expression $CIC(CB)I$, we can make the following letter assignment:

$$\underbrace{C}_{C}\underbrace{I}_{x}\underbrace{C}_{y}\underbrace{(CB)}_{z}I$$

and see that $CIC(CB)I ≡ (((CI)C)(CB))I ≡ (((Cx)y)z)I$ contains the $C$ combinator pattern and thus reduces to $((xz)y)I ≡ I(CB)CI$:

$$(\underbrace{C}_{C}\underbrace{I}_{x}\underbrace{C}_{y}\underbrace{(CB)}_{z})I \rightarrow (\underbrace{I}_{x}\underbrace{(CB)}_{z}\underbrace{C}_{y})I$$

One more example: $B((CK)I)IC$ expression. Let us first reduce combinator $B$:

$$(\underbrace{B}_{B}\underbrace{((CK)I)}_{x}\underbrace{I}_{y}\underbrace{C}_{z} \rightarrow \underbrace{((CK)I)}_{x}(\underbrace{I}_{y}\underbrace{C}_{z})$$

Now, let's reduce the last $I$:

$$((CK)I)(\underbrace{I}_{I}\underbrace{C}_{x}) \rightarrow ((CK)I)C$$

And now we finish evaluation with two more reductions:

$$((\underbrace{C}_{C}\underbrace{K}_{x})\underbrace{I}_{y})\underbrace{C}_{z} \rightarrow (\underbrace{K}_{K}\underbrace{C}_{x})\underbrace{I}_{y} \rightarrow C$$

It is possible to show that the normal form remains the same irrespective of the order of evaluation. For example, the following evaluation order:

$$C(K(II)(\underbrace{I}_{I}\underbrace{C}_{x})) \rightarrow C(K(\underbrace{I}_{I}\underbrace{I}_{x})(C)) \rightarrow C((\underbrace{K}_{K}\underbrace{I}_{x})\underbrace{C}_{y}) \rightarrow CI$$

leads to the same result as:

$$C(K(\underbrace{I}_{I}\underbrace{I}_{x})(IC)) \rightarrow C((\underbrace{K}_{K}\underbrace{I}_{x})\underbrace{(IC)}_{y}) \rightarrow CI$$

However, as you see, the number of reductions is different: $3$ in the first case and $2$ in the second. This poses an interesting problem—to find an evaluation order with the minimal number of reductions for a given formula.

Your task is to write a program that finds the minimal number of reductions required for a given combinator expression to be evaluated to its normal form.

## Input Format

The only line of the input file contains a combinator expression corresponding to the grammar above. The length of the expression does not exceed $30,000$. The expression contains no whitespaces or symbols not specified in the grammar.

## Output Format

Output a single integer—the minimal number of reductions required for the given formula to evaluate it to normal form.

## Sample Input and Output

### Sample Input #1

```
C(K(II)(IC))
```

### Sample Output #1

```
2
```

### Sample Input #2

```
CIBI
```

### Sample Output #2

```
3
```

### Sample Input #3

```
BBBBBCCCCCKKKKKIIIII
```

### Sample Output #3

```
15
```

## Notes/Hints

Time limit: 1 second, Memory limit: 256 MB.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
