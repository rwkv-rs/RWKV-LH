Program analysis techniques are methods used to understand and improve computer programs. They help us identify errors in programs, enhance performance, and optimize code structure. Among these techniques, static analysis examines program code without executing it. It can check syntax, style, and potential errors. For example, static analysis can help us find unused variables and possible array out-of-bounds issues in a program.

Xiao Xiao has designed his own programming language, named X Language. Can you design a static analyzer for it?

An X Language program only uses two integer variables, $x$ and $y$, which do not need to be defined and can be used directly. The value of variable $x$ is input from outside the program (the input value can be any value within the C++ int range), and $y$ is initialized to $0$. An X Language program consists of several lines, each containing exactly one command, which is one of the following three types:
1. Conditional branch: `if (condition) {`;
2. Assignment to $y$: `y = number;`;
3. End of condition: `}`.

The "condition" can either be `x > number` or `x < number`. The "number" in assignments and conditions is a constant between $1$ and $10^9$. The meanings of `if` and assignments are the same as in C++ language.

Please write a static analyzer to analyze all possible values of $y$ when the X Language program finishes execution.

## Input Format

The first line of the input data is an integer $n$, representing the number of lines in the program.

The next $n$ lines each contain a command, describing a valid X Language program: The input program is guaranteed to have matching brackets and conform to the conventions described in the problem. For ease of parsing (e.g., using `cin` or `scanf`), there is exactly one space around `if`, `{`, `=`, `<`, and `>` in the input program, and there may be several spaces at the beginning of each line for indentation. Apart from this, the input does not contain extra spaces or blank characters.

## Output Format

Output one line, listing all possible values of variable $y$ at the end of the program in ascending order without repetition. Numbers should be separated by a space.

## Sample Input and Output

### Sample Input #1

```
10
if (x > 1) {
  y = 2;
  if (x > 10) {
    y = 1;
    y = 4;
    if (x < 5) {
      y = 3;
    }
  }
}
```

### Sample Output #1

```
0 2 4
```

### Sample Input #2

```
(See p4.zip for 2-in.txt)
```

### Sample Output #2

```
(See p4.zip for 2-out.txt)
```

### Sample Input #3

```
(See p4.zip for 3-in.txt)
```

### Sample Output #3

```
(See p4.zip for 3-out.txt)
```

## Notes

For $100\%$ of the data, it is guaranteed that $1 \le n \le 10^3$. Each line of the input data does not exceed $10^3$ characters.

> The original full score for this problem was $20\text{pts}$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
