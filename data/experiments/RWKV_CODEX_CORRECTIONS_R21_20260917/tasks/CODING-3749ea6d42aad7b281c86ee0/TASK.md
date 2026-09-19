Calculate the value of the expression given in the specified format and take the modulus of $2011$.

The BNF (Backus–Naur Form) of the expression is defined as follows:

```
<expr> ::= <term> | <expr> <'.'> <'+'|'-'> <'.'> <term>
<term> ::= <factor> | <term> <'.'> <'*'> <'.'> <factor>
<factor> ::= <powexpr> | <fraction> | <'-'> <'.'> <factor>

                                    <digit>
<powexpr> ::= <primary> | <primary>

<primary> ::= <digit> | <'('> <'.'> <expr> <'.'> <')'>

                <expr>    
<fraction> ::= --------
                <expr>
                
<digit> ::= '0' | '1' | ... | '9'
```

Below is an example of the concrete form of expressions (specific content can be seen in the original PDF).

![Specific Form](https://cdn.luogu.com.cn/upload/image_hosting/z9tlmgr0.png)

## Semicolon Format Issue

For example, when $-\frac{4}{3}$ is split into $3$ lines, the unary operator (negative sign) requires a space for separation.

```
   3
- ---
   4
```

Another example, the fraction $\frac{3+4\times -2}{-1-2^2}$ is written over $4$ lines.

```
 3 + 4 * - 2
-------------
          2
   - 1 - 2
```

The width of the numerator is $11$ and the width of the denominator is $8$. Therefore, the length of the horizontal line of the denominator is $2+\max(11,8)= 13$.

The shorter part (in this case the denominator) should be padded with spaces: $\lceil \frac{13-8}{2}\rceil$ spaces on the left and $\lfloor \frac{13-8}{2}\rfloor$ spaces on the right.

## Exponent Expression Issues

For example, $(4^2)^3$ is written in just $2$ lines (clearly it is not the same as $4^{2^3}$).

```
   2  3
( 4  )
```

Essentially, both the parentheses and the expression inside should be spaced, while the outer exponent stays adjacent horizontally.

Note the alignment of vertical indices with syntactic components, where $3$ corresponds to the exponent of $(4^2)$, so it aligns with $2$ on the same line.

## Input & Output

Multiple sets of input data until a $0$ is encountered. Each time, read the number of expression lines $n$, followed by $n$ lines of expression.

For each set of data, ensure that the number of lines does not exceed $20$ and the number of columns does not exceed $80$.

Output the actual result modulus $2011$ for each data set (evidently the original result is a rational number). It is guaranteed that neither $0$ nor a multiple of $2011$ will appear in the denominator.

### Input Sample

```
4
........4...2..........
(.1.-.----.)..*.-.5.+.6
........2..............
.......3...............
3
...3.
-.---
...4.
4
.3.+.4.*.-.2.
-------------
..........2..
...-.1.-.2...
2
...2..3
(.4..).
1
2.+.3.*.5.-.7.+.9
1
(.2.+.3.).*.(.5.-.7.).+.9
3
.2....3.
4..+.---
......5.
3
.2......-.-.3.
4..-.-.-------
..........5...
9
............1............
-------------------------
..............1..........
.1.+.-------------------.
................1........
......1.+.-------------..
..................1......
...........1.+.-------...
................1.+.2....
15
.................2......
................---.....
.......2.........5....3.
.(.---------.+.-----.)..
.....7...........3......
....---.+.1.............
.....4..................
------------------------
.......2................
......---...............
.......5.......2....2...
...(.-----.+.-----.)....
.......3.......3........
..............---.......
...............4........
2
.0....2....
3..+.4..*.5
20
............2............................2......................................
...........3............................3.......................................
..........----.........................----.....................................
............4............................4......................................
.....2.+.------.+.1...............2.+.------.+.1................................
............2............................2......................................
...........2............................2........................2..............
..........----.........................----.....................3...............
............2............................2.....................----.............
...........3............................3........................4..............
(.(.----------------.+.2.+.3.).*.----------------.+.2.).*.2.+.------.+.1.+.2.*.5
............2............................2.......................2..............
...........5............................5.......................2...............
..........----.........................----....................----.............
............6............................6.......................2..............
.........------.......................------....................3...............
............3............................3......................................
..........----.........................----.....................................
............2............................2......................................
...........7............................7.......................................
0
```

### Output Sample

```
501
502
1
74
19
2010
821
821
1646
148
81
1933
```
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
