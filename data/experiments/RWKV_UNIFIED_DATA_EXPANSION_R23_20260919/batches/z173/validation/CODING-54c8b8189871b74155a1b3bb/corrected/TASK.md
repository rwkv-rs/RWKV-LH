In this problem, the J language is an expression that adheres to the following Backus-Naur Form (BNF):
```
<expression> ::= <term> | <term> ('+' | '-' | '*') <expression> | ('-' | '*:' | '+/') <expression>
<term> ::= '(' <expression> ')' | 'X' | 'N' | <number>
<number> ::= ('0' | '1' | ... | '9')+
```
For a binary operator, when the operands are a number and a vector, it operates by performing the calculation on each component of the vector with the number. When the operands are two vectors, it operates by performing the calculation on each corresponding component of the vectors. Notably, all vectors in this problem are identical.

The symbols in the Backus-Naur Form are explained as follows:
- Addition, subtraction, and multiplication operations `'+', '-', '*'`
- Unary operations `'-', '*:', '+/'`. `-A` denotes the negation of A, `*:A` denotes the squaring of A, and `+/A` is called **folding**, which sums all components of vector A.
- Parentheses `'(', ')'`. Without parentheses, all operators have the same precedence, and parentheses can alter the order of operations, similar to conventional usage.
- Numbers.
- Letters `'N', 'X'`. N is equivalent to a predetermined number, and X is equivalent to a predetermined vector.
- Units. Expressions, numbers, and letters are collectively referred to as units.
- Expressions. A string formed by connecting units with binary and unary operators in a syntactically correct manner is called an expression. Expressions must not contain any characters not mentioned above.
- Note: Expressions in the J language are **right-associative**, meaning they are evaluated from right to left. However, for non-commutative subtraction, we stipulate that `A-B` still means A minus B, not B minus A. For numbers, we stipulate that they are read from left to right. For example, `123` should be understood as 100 + 20 + 3, not 300 + 20 + 1.

Each expression is defined with a **complexity**. We stipulate that the complexity of all numbers (scalars) is 0, the complexity of `X` is 1, the complexity of addition and subtraction operations `A+B, A-B` is the maximum of the complexities of A and B. The complexity of `A*B` is the sum of the complexities of A and B. Unary negation does not change the complexity of the expression, squaring doubles the complexity of the expression, and folding reduces the complexity to 0.

You need to read in $N, X (N \le 10^5)$, ensuring that N equals the length of X. All components of X are positive integers not exceeding $10^9$. Then, read a single line containing an expression `expr`, ensuring its complexity does not exceed 10, its length does not exceed $10^5$ characters, and it fully adheres to the syntactic rules. You are required to compute the value of `expr` modulo $10^9$ (ensuring the result is a scalar, not a vector).

## Input Format

The first line contains one integer $N (1 \le N \le 10^5)$ — the length of the vector $X$.

The second line contains $N$ integers — the components of the vector $X (0 \le X_i < 10^9)$.

The third line contains the expression to be computed, a non-empty string of no more than $105$ symbols. Each number in the expression is less than $109$. The fold is never applied to a scalar.

## Output Format

Output a single integer number — the result of the expression modulo $10^9$.

## Sample Input and Output

### Input Sample #1
```
5
1 2 3 4 5
+/*:X
```

### Output Sample #1
```
55
```

### Input Sample #2
```
5
1 2 3 4 5
N++/X-X+1
```

### Output Sample #2
```
0
```

### Input Sample #3
```
3
11 56 37
+/(3-+/*:*:X)-X**:X
```

### Output Sample #3
```
964602515
```

## Notes/Hints

Time limit: 2 seconds, Memory limit: 256 MB.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
