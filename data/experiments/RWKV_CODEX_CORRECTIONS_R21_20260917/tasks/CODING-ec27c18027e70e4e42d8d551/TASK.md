For each input number \( n \), output the prime factorization of \( n \).

- If \( n \) is positive: \( n = f_1 \times f_2 \times f_3 \times \ldots \times f_x \)

- If \( n \) is negative: \( n = -1 \times f_1 \times f_2 \times \ldots \times f_x \)

(All \( f_i \) are prime numbers and satisfy \( f_1 \leq f_2 \leq f_3 \leq \ldots \))

The program terminates when \( n \) is 0 (no need to consider the case where \( n \) is positive or negative 1).

\(-2^{31} < n < 2^{31}\)

## Input and Output Example

### Input Example #1

```
-190
-191
-192
-193
-194
195
196
197
198
199
200
0
```

### Output Example #1

```
-190 = -1 x 2 x 5 x 19
-191 = -1 x 191
-192 = -1 x 2 x 2 x 2 x 2 x 2 x 2 x 3
-193 = -1 x 193
-194 = -1 x 2 x 97
195 = 3 x 5 x 13
196 = 2 x 2 x 7 x 7
197 = 197
198 = 2 x 3 x 3 x 11
199 = 199
200 = 2 x 2 x 2 x 5 x 5
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
