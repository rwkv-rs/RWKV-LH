IA is a girl who can sing.

As IOI2018 approaches, IA decides to compose a song for the contestants to express her best wishes. The song consists of \( n \) notes, with the pitch of the \( i \)-th note being \( h_i \). IA's vocal range is \( A \), meaning she can only sing pitches that are positive integers from \( 1 \) to \( A \). Therefore, \( 1 \le h_i \le A \).

Before composing the song, IA needs to determine its structure. She writes down \( Q \) constraints, where the \( i \)-th constraint states that the highest pitch among the notes from \( l_i \) to \( r_i \) is \( m_i \). After determining the structure, she can start composing the song. However, she wonders how many possible songs satisfy all her constraints. She heard that you are going to IOI in 9 months and hopes you can help her calculate this number.

## Input Format

Data is read from standard input.

The first line contains an integer \( T \) (\( T \le 20 \)), representing the number of test cases.

For each test case, the first line contains three positive integers \( n \), \( Q \), and \( A \). The next \( Q \) lines each contain three integers \( l_i \), \( r_i \), and \( m_i \), representing a constraint. It is guaranteed that \( 1 \le l_i \le r_i \le n \) and \( 1 \le m_i \le A \).

## Output Format

Output is written to standard output.

The output file should contain one line, representing the number of possible songs. Since this number can be very large, output the answer modulo \( 998244353 \).

## Sample Input and Output

### Sample Input #1

```
1
3 2 3
1 2 3
2 3 2
```

### Sample Output #1

```
3
```

### Sample Input #2

```
2
4 2 4
1 2 3
2 3 4
7 3 74
3 6 56
2 5 56
3 7 70
```

### Sample Output #2

```
20
160326468
```

## Notes

**Sample 1 Explanation**
The following are three possible songs: \((3,1,2)\), \((3,2,1)\), \((3,2,2)\).

![0](https://cdn.luogu.com.cn/upload/pic/14340.png)

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
