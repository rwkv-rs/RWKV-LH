According to Java standard library documentation, the hash code of a String is computed as:

$$s[0] \times 31 ^ {n -1} + s[1] \times 31 ^ {n -2} + \cdots + s[n -1]$$

Here, $s[i]$ is the i-th character of the string, $n$ is the length of the string, and $^$ indicates exponentiation. The computation uses signed 32-bit integers in two's complement form.

Heather is planning to hack the servers of Not Entirely Evil Recording Company (NEERC). To perform an attack, she needs $k$ distinct query strings that have equal hash codes. Unfortunately, NEERC servers only accept query strings containing lowercase and uppercase English letters.

Heather has hired you to write a program that generates such query strings for her.

## Input Format

The input file contains a single integer $k$ — the number of required query strings to generate $(2 \le k \le 1000)$.

## Output Format

Output $k$ lines. Each line should contain a single query string. Each query string should be non-empty and its length should not exceed 1000 characters. Query strings should contain only lowercase and uppercase English letters. All query strings should be distinct and should have equal hash codes.

## Sample Input and Output

### Sample Input #1

```
4
```

### Sample Output #1

```
edHs
mENAGeS
fEHs
edIT
```

## Notes/Hints

Time limit: 2 seconds, Memory limit: 256 MB.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
