You are given $t$ sets of data. For each set, you are provided with three numbers: $x, y, n$. Your task is to compute $x^y \mod n$.

---

The first line of input contains an integer $t$, indicating the number of data sets.  
The next $t$ lines each contain three integers: $x, y, n$.  
After all the data has been input, there is an additional line with a single $0$.

---

For each data set, output a single line containing an integer that represents the result of $x^y \mod n$.

---

Sample Input:

```
2
2 3 5
2 2147483647 13
0
```

Sample Output:

```
3
11
```

---

Data constraints: $1 < x, n < 2^{15}, 0 < y < 2^{31}$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
