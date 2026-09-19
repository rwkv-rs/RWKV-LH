As is well known, Xiao L loves using "123321" as a password. Every time he logs into Codeforces, he sees a prominent warning:

```text
Your password is extremely weak or has been leaked. Please, change it ASAP. 
(see https://haveibeenpwned.com/)
```

## Problem Description

After being thoroughly defeated, Xiao L decided to use a more secure password. He designed a password consisting of only lowercase letters, potentially up to 200,000 characters long, ensuring that no one could memorize, guess, or try it out (including himself).

To prevent himself from forgetting the entire password (it's already forgotten), Xiao L wrote a program to store his password string \( T \), but it cannot directly output the password (as the program might be used by others). Xiao L will first reconstruct a string \( P \) of length \( l \) from memory, and then modify a specific character of \( P \) based on the program's output. The program calculates the **mismatch degree** between the current guess string \( P \) and a substring of \( T \) of the same length.

Define the value of character 'a' as 1, character 'b' as 2, and so on, with character 'z' being 26. The mismatch degree between two strings \( s \) and \( t \) is defined as the square of the difference in values at corresponding positions.

Now, Xiao L wants to know if his program is correct, and asks you to write a similar program.

## Input Format

The first line of input contains three numbers \( n, l, m \), representing the length of the password string \( T \), the length of the guess string \( P \), and the number of operations, respectively.

The next two lines contain the strings \( T \) and \( P \), respectively.

The following \( m \) lines, each starting with an integer \( op \), indicate the type of operation:

- If \( op = 1 \), there is an additional integer \( x \), indicating to calculate the mismatch degree between \( P \) and the substring of \( T \) starting at the \( x \)-th position with length \( l \).
- If \( op = 2 \), there are additional integer \( x \) and character \( c \), indicating to modify the \( x \)-th character of \( P \) to \( c \).

## Output Format

For each operation of type 1, output a line containing the calculated mismatch degree.

## Sample Input and Output

### Sample Input #1

```
8 5 3
iamangry
anger
1 4
2 2 m
1 2
```

### Sample Output #1

```
218
238
```

## Notes/Hints

**Please note the special time limit for this problem.**

**Given the large data scale, pay attention to constant optimization.**

To prevent excessive optimization requirements, this problem **provides [Octuple Oxygen](https://www.luogu.com.cn/paste/ky1fh8zk)**, which can be directly added at the beginning of the code for submission.

All indices in this problem start from 1.

- Subtask #1: 30 points, guaranteed \( n, m \leq 5 \times 10^3 \);
- Subtask #2: 30 points, guaranteed no operation of type 2;
- Subtask #3: 40 points, guaranteed \( n, m \leq 2 \times 10^5 \).

For 100% of the data, it is guaranteed that \( 1 \leq l \leq n, 1 \leq x \).

For all operations of type 1, it is guaranteed that \( x-1+l \leq n \).

For all operations of type 2, it is guaranteed that \( x \leq l \).

### Sample Explanation

\((a-a)^2+(n-n)^2+(g-g)^2+(r-e)^2+(y-r)^2 = 13^2 + 7^2 = 218\).

\((a-a)^2+(m-m)^2+(a-g)^2+(n-e)^2+(g-r)^2 = 6^2 + 9^2 + 11^2 = 238\).

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
