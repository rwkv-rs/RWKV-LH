The new version of beloved programming language Fygon has been released! The brand new Fygon 2.0 still has only two statements. The first statement is `lag`. It substitutes almost any other statement. The second statement is a `for` loop:

```
for <variable> in range(<from>, <to>):
    <body>
```

The `for` loop makes `<variable>` iterate from `<from>` to `<to>`, both inclusive.

If `<from>` is greater than `<to>`, the loop is not executed at all.

`<variable>` is a lowercase letter from `a` to `z`, except for `n`, which is a variable that is defined prior to the given code snippet.

`<from>` and `<to>` can be equal to any variable defined in outer loops. In addition to that, `<from>` can be `1` and `<to>` can be `n`.

The body of the loop is indented by four spaces and contains at least one statement.

If you are familiar with Fygon 1.0, you can notice that, in the spirit of the best programming practices, Fygon 2.0 is not backwards compatible, since the range function now requires two parameters.

The performance of the new version is significantly improved, so you can write more nested for loops. That is why we are no longer interested in the exact number of operations, but in the asymptotic complexity of the program instead. For simplicity, all for loops are nested in a single chain and there is exactly one `lag` statement that is inside all for loops. All loop variables are different and are not equal to `n`.

Let's define \( f(n) \) as the number of `lag` operations executed by a given Fygon program as the function of \( n \). For non-negative integer \( k \) and positive rational number \( C \) we say that \( C \cdot n^k \) is the asymptotic complexity of the program if

\[
\lim_{n \to \infty} \frac{f(n)}{C \cdot n^k} = 1
\]

Given a Fygon 2.0 program, find its asymptotic complexity.

## Input Format

The first line of the input contains a single integer \( m \) -- the number of lines in the Fygon 2.0 program. Next \( m \) lines contain the program itself. The program has at least 1 and at most 20 `for` statements. Each `for` statement contains either a single nested `for` statement or a `lag` statement.

## Output Format

Output numbers \( k \) and \( C \). \( C \) should be output in the form of an irreducible fraction \( p/q \), where \( p \) and \( q \) are coprime.

## Sample Input and Output

### Input Sample #1

```
4
for i in range(1, n):
    for j in range(1, i):
        for k in range(j, n):
            lag
```

### Output Sample #1

```
3 1/3
```

## Notes/Hints

Time limit: 3 s, Memory limit: 512 MB.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
