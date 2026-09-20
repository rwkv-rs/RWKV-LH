In the human nervous system, each signal can be represented by -1 or +1. These signals combine to form various complex information such as emotions, tastes, and colors. The breakthrough in nanoscale detection technology allows biologists to measure the complete logical functions of specific brain regions. However, the processing of extremely large datasets has always been a headache for Professor H.

Suppose a logical unit receives N input signals and produces a real value r representing a certain meaning. There are a total of 2^N possible scenarios. Through long-term cumulative measurements, Professor H can accurately obtain the relationship table between input signals and r:

$$f :{-1,1}^N \to \mathbb{R} $$

Further research has shown that the operation of neurons can be modeled as a polynomial that is familiar to us. Since the square of an input signal value is always 1, we can uniquely represent any logical function f with a polynomial of 2^N terms without powers.

For example:
$x_1=+1; x_2=+1 \to 0$

$x_1=+1; x_2=-1 \to 1$

$x_1=-1; x_2=+1 \to 2$

$x_1=-1; x_2=-1 \to 3$

can be written as:

$$f(x_1,x_2)=1.5-0.5x_2-x_1$$

Studying the polynomial form of a logical unit is very significant for understanding how the brain works. Therefore, Xiao M decided to help Professor H convert all the measured logical relationship tables into polynomial forms. This simple task should not be a problem for the programming expert Xiao M, right?

## Input Format

The first line is N (1≤N≤20), followed by 2^N lines. Each line is a set of logical inputs and a corresponding value, representing the signs of x_1...x_N and the corresponding r. See the sample for details. The data guarantees that the absolute value of all logical values does not exceed 100 and does not contain more than 2 decimal places. It is guaranteed that all logical input strings are unique.

## Output Format

A maximum of 2^N lines, representing the coefficients of each term of the polynomial. If the answer is an integer, output it in integer form. Otherwise, output it in the simplest fraction form. If the coefficient is exactly 0, omit the entire line. Variables and coefficients are separated by spaces, and the constant term does not need to be separated by a space.

The order follows the lexicographical order of the polynomial:

1. The constant term is first;
2. In the absence of a constant term, terms with smaller minimum x indices are prioritized;
3. When two terms have the same smallest index, compare recursively by the same rule after removing the smallest index x.

Example: 1, x1, x1x2, x1x2x3, x1x3, x2, x2x3, x3. See the sample for details.

## Sample Input and Output

### Input Sample #1

```
2 
++ 0 
+- 1 
-+ 2 
-- 3 
```

### Output Sample #1

```
3/2 
-1 x1 
-1/2 x2 
```

### Input Sample #2

```
3 
--- -1.0
-++ -1.0
+-+ -1.0
++- -1.0
--+ 1.0
-+- 1.0
+-- 1.0
+++ 1.0
```

### Output Sample #2

```
1 x1x2x3
```

## Notes/Hints

There are a total of 10 test cases.

For the first case, N≤3;

For the second case, N≤8;

For the third and fourth cases, N≤11;

For the fifth and sixth cases, the answer polynomial has only one non-zero term, as in Sample #2.

For the seventh and eighth cases, the answer polynomial has at most 5 non-zero terms.

For 100% of the data, $1 \le N \le 20, |r| \le 100, 100r \in \mathbb{Z}$.

Friendly reminder:

Please pay attention to the efficiency of input and output.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
