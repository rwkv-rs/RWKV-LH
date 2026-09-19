As is well known, passwords play an invaluable role in the field of information. For ordinary login passwords, the only method of cracking is brute force—trying all possible combinations of letters, which is a time-consuming and easily detectable task. Therefore, before attempting to brute force a password, extensive preparation must be done. After gathering intelligence, we have obtained several useful pieces of information, such as:

> "I have observed that the password contains the string *."

For example, for a 10-character password and observed strings `hello` and `world`, possible password combinations are `helloworld` and `worldhello`; for a 6-character password and observed strings `good` and `day`, the possible password combination is `gooday`.

With this information, the number of attempts can be significantly reduced. Please write a program to calculate all possible password combinations. The password may only contain lowercase letters from `a-z`.

## Input Format

The input data starts with two integers $L, N$, representing the length of the password and the number of observed substrings, respectively.

The next $N$ lines each contain several characters, describing each observed substring.

## Output Format

The first line of the output data is an integer representing the total number of strings that satisfy all observed conditions.

If this number is less than or equal to 42, output all possible passwords in lexicographical order, one per line; otherwise, output only the total number of strings that satisfy all observed conditions.

## Sample Input and Output

### Sample Input #1

```
10 2
hello
world
```

### Sample Output #1

```
2
helloworld
worldhello
```

## Notes/Hints

For $100\%$ of the data, $1 \leq L \leq 25, 1 \leq N \leq 10$, each observed substring is no longer than 10 characters, and the output result is guaranteed to be less than $2^{63}$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
