Frederick is a young programmer. He participates in all programming contests he can find and always uses his favorite programming language Fygon. Unfortunately, he often receives "Time Limit Exceeded" results, even when his algorithm is asymptotically optimal. This is because the Fygon interpreter is very slow. Nevertheless, Frederick likes Fygon so much that he uses non-asymptotic optimizations to fit the solution within the time limit. To make it easier, he asks you to write a program that can estimate the exact number of operations his Fygon program performs.

For simplicity, we assume that Fygon has only two statements. The first statement is "lag," which can substitute almost any other statement. The second statement is a for loop:

```
for in range $():$
```

This means that iterates over values from $0$ to $−1$. In Fygon, is a lowercase letter from $a$ to $z$, and is either already defined or a positive integer constant. The body of the loop is indented by four spaces and contains at least one statement.

The program receives input in the variable $n$. This variable has special meaning and cannot be used as a loop variable. Your task is to find the formula that calculates the number of "lag" operations performed by the given Fygon program, depending on the value of the variable $n$.

## Input Format

The input file contains the Fygon program. No two loops use the same variable as iterators. Each variable used inside a range is either $n$ or declared in some outer loop.

The program has at most $20$ statements, with at most $6$ of them being loops. All integer constants range from $1$ to $9$.

## Output Format

Output the formula for the number of performed "lag" operations depending on $n$. The length of the formula should be at most $100$ characters (excluding spaces). The formula should conform to the following grammar:

```
〈Expression〉 ::= 〈Product〉 ( (‘+' | ‘-') 〈Product〉) *
〈Product〉 ::= 〈Value〉 (‘*'〈Value〉) *
〈Value〉 ::= ‘n' | 〈Number〉 | ‘-'〈Value〉 | ‘('〈Expression〉‘)'
〈Number〉 ::= [‘0' … ‘9'] + (‘/' [‘0' … ‘9'] +)?
```

## Sample Input and Output

### Sample Input #1

```
for i in range(n):
    for j in range(i):
        lag
for x in range(5):
    for y in range(n):
        for z in range(n):
            lag
    lag
```

### Sample Output #1

```
1/2 * n * (n-1) + 5 * (n*n + 1)
```

## Notes/Hints

Time limit: 2 seconds, Memory limit: 256 MB.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
