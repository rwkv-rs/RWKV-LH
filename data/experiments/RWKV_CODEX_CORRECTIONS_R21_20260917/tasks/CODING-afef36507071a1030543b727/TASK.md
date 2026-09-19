In order to help Otsukasa Yuu recover his memory, Tomori Nao sought the help of PZY.

PZY's research revealed that abilities are primarily determined by the body's ability genes. He identified a total of \( m \) ability genes, denoted by numbers from 1 to \( m \), and divided them into \( n \) sets. The \( i \)-th set contains \( a_i \) ability genes with numbers ranging from \((\sum_{j=1}^{i-1} a_j) + 1\) to \(\sum_{j=1}^{i} a_j\).

Through extensive experiments, PZY found that the arrangement of genes could be simplified into a sequence. A sequence is defined as a gene sample if and only if it consists of numbers from 1 to \( m \), and for numbers belonging to the \( i \)-th set, they must be **non-strictly monotonically increasing** in the sequence and appear no more than \( b_i \) times.

Specifically, the research value of a gene sample is the sum of all the numbers in the sequence, including repeated numbers.

To aid Otsukasa Yuu in recovering his memory, PZY wants to know the sum of the research values of all possible gene samples.

Since the answer can be very large, he only needs to know the remainder of the answer when divided by \( 998244353 \).

## Input Format

The first line contains a positive integer \( n \).

From the second to the \( n+1 \)-th line, each line contains two positive integers \( a_i \) and \( b_i \), as described in the problem statement.

## Output Format

Output the remainder of the sum of the research values of all gene samples when divided by \( 998244353 \).

## Sample Input and Output

### Sample Input #1

```
2
2 2
1 2
```

### Sample Output #1

```
300
```

### Sample Input #2

```
3
2 2
3 6
2 4
```

### Sample Output #2

```
661677771
```

## Notes

Explanation of Sample #1:

The two sets are \(\{ 1, 2 \}\) and \(\{ 3 \}\).

For gene samples of length 1: \( 1, 2, 3 \).  
Total value: \( 1 + 2 + 3 = 6 \).

For gene samples of length 2: \( 11, 12, 13, 22, 23, 31, 32, 33 \).  
Total value: \( 1 + 1 + 1 + 2 + 1 + 3 + 2 + 2 + 2 + 3 + 3 + 1 + 3 + 2 + 3 + 3 = 33 \).  
The sequence \( 21 \) does not satisfy the non-strictly monotonically increasing condition for set 1.

For gene samples of length 3: \( 113, 123, 131, 132, 133, 223, 232, 233, 311, 312, 313, 322, 323, 331, 332 \).  
Total value: \( 99 \).  
Sequences \( 111, 112, 122, 222, 333 \) exceed the occurrence limit.

For gene samples of length 4, the total value is \( 162 \).

Thus, the total value is \( 6 + 33 + 99 + 162 = 300 \).

---

Let \( k = \sum_{i} b_i \).

For 10% of the data: \( 1 \le n \le 3, 1 \le k \le 10, 1 \le a_i \le 5 \).  
For another 20% of the data: \( n = 1, 1 \le k \le 10^5, 1 \le a_i \le 10^6 \).  
For another 30% of the data: \( n = 2, 2 \le k \le 10^5, 1 \le a_i \le 10^6 \).  
For 100% of the data: \( 1 \le n \le k \le 10^5, 1 \le a_i \le 10^6 \).

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
