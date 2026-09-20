### General Idea

A float-type floating-point number is composed of 16 binary bits.

The first bit is the sign bit, the second to eighth bits are the exponent, and the ninth to sixteenth bits are the mantissa.

![](https://pic.imgdb.cn/item/64b4f6f91ddac507cc4ad4b1.jpg)

The number is represented in decimal as $-10.375$.

- If the sign bit is $1$, the number is negative.
- The exponent minus $63$ is the actual exponent, with a base of $2$. (In this example, $(1000010)_2-63=3$)
- The remaining mantissa represents the binary digits after the decimal point, while the digits before the decimal are always $1$.

![](https://pic.imgdb.cn/item/64b4f7f81ddac507cc4e3d76.jpg)

- Therefore, the number is $-10.375$ in decimal, and in programming, it is generally written as $\texttt{-1.0375e+001}$. Different programming languages may vary in the uppercase/lowercase of $\texttt{e}$ and the number of leading zeros in the exponent.
- Special Case: If all bits except the sign bit are $0$, the number is $0$.

### Input Format

Each line contains 16 binary bits.

### Output Format

A line of 14 characters representing the float-type floating-point number in decimal:

- The 1st character is a space for positive numbers, or $\texttt{-}$ for negative numbers.
- Characters 2 to 9 represent a floating-point number precise to six decimal places.
- The 10th character is $\texttt{e}$.
- The 11th character is $\texttt{+}$ or $\texttt{-}$ indicating the sign of the exponent. (If the exponent is $0$, it is $\texttt{+}$)
- Characters 12 to 14 represent the exponent, padded with leading zeros if not three digits.

### Sample Input

```
1100001001001100
0011111100000000
1011111110000000
0000000010101010
0011011111100000
1001111011100000
0101011001010101
0100011011101101
0111111111111111
1100001000101100
0000000000000000
1000000000000000
```

### Sample Output

```
-1.037500e+001
 1.000000e+000
-1.500000e+000
 1.804180e-019
 7.324219e-003
-2.182787e-010
 1.117389e+007
 2.465000e+002
 3.682143e+019
-9.375000e+000
 0.000000e+000
 0.000000e+000
```
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
