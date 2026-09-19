yltx is once again stumped by a problem he can't solve...

## Problem Description

yltx defines a **prime** number pair \((x, y)\) as a yltx number pair if \(x \times y - 3 \times (x - y)\) is a prime number.

He has given you \(T\) pairs \((x, y)\), and you need to check if they are yltx number pairs.

The data is given in the form of a seed \((x_0, y_0)\).

Perform \(T\) iterations where \(x_0 \leftarrow (7x_0 + 13) \ \mathrm{xor} \ (x_0 \div 13 - 7)\). For the \(i\)-th iteration, the resulting number is first taken modulo \(10^4\), added to \(10^4\), taken modulo \(10^4\), and then incremented by 1 to get the \(i\)-th data's \(x\). The division here is integer division, treating \(x_0\) as a 32-bit signed integer.

Use the same method to obtain \(y\).

Data generation template:

```cpp
#include<bits/stdc++.h>
using namespace std;
int T, x_0, y_0;
int main() {
    scanf("%d%d%d", &T, &x_0, &y_0);
    while (T--) {
        x_0 = ((7 * x_0 + 13) ^ (x_0 / 13 - 7));
        y_0 = ((7 * y_0 + 13) ^ (y_0 / 13 - 7));
        int x = (x_0 % 10000 + 10000) % 10000 + 1, y = (y_0 % 10000 + 10000) % 10000 + 1;
        // x, y is a pair (x, y).
    }
    return 0;
}
```

## Input Format

The first line contains three integers \(T, x_0, y_0\).

## Output Format

Output a single line, the number of pairs that are yltx number pairs.

## Sample Input and Output

### Input Example #1

```
100000 1 2
```

### Output Example #1

```
321
```

## Notes/Hints

The data range for each test point is as follows:

| Test Point | T | Subtask |
| :---: | :---: | :---: |
| 1 | \(\le 10\) | 1 |
| 2 | \(\le 20\) | 1 |
| 3 | \(\le 50\) | 1 |
| 4 | \(\le 100\) | 1 |
| 5 | \(\le 500\) | 1 |
| 6 | \(\le 1000\) | 1 |
| 7 | \(\le 5000\) | 2 |
| 8 | \(\le 10^4\) | 2 |
| 9 | \(\le 5 \times 10^4\) | 2 |
| 10 | \(\le 4 \times 10^5\) | 2 |
| 11 | \(\le 10^6\) | 2 |
| 12 | \(\le 5 \times 10^6\) | 2 |
| 13 | \(\le 4 \times 10^7\) | 3 |
| 14 | \(\le 4 \times 10^7\) | 3 |
| 15 | \(\le 4 \times 10^7\) | 3 |
| 16 | \(\le 4 \times 10^7\) | 3 |
| 17 | \(\le 4 \times 10^7\) | 3 |
| 18 | \(\le 4 \times 10^7\) | 3 |
| 19 | \(\le 4 \times 10^7\) | 3 |
| 20 | \(\le 4 \times 10^7\) | 3 |

Each Subtask is bundled for testing.

This problem allows data download, but we hope you use the data for the right purposes.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
