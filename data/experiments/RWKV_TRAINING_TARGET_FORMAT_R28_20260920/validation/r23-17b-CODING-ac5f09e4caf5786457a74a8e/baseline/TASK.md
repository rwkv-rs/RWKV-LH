Convert all real numbers in the interval $[0,1]$ into base-three notation (there may be multiple ways to do this), for example:

- $1=1_{(3)}=0.2222\cdots_{(3)}$
- $0=0_{(3)}=0.0000\cdots_{(3)}$
- $0.875=0.212121\cdots_{(3)}$

If there exists **at least one** base-three conversion for a real number in the interval $[0,1]$ that does not contain the digit `1`, then the number is part of the `Cantor Set`.

For example, $1$ and $0$ are part of the `Cantor Set`, whereas $0.875$ is not since its conversion always includes the digit `1`.

---

The input consists of an indeterminate number of data groups, ending with `END`.

Each line contains a real number $x (0 \leq x \leq 1)$ with up to six decimal places. Determine if $x$ belongs to the `Cantor Set`.

Output `MEMBER` if it belongs; otherwise, output `NON-MEMBER`.

## Input/Output Sample

### Input Sample #1

```
0
1
0.875
END
```

### Output Sample #1

```
MEMBER
MEMBER
NON-MEMBER
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
