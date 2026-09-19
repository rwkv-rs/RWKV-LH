In this problem, hexadecimal notations use 0, ..., 9, A, ..., F, representing the values zero through fifteen, respectively.
Unless otherwise specified, all notations of numbers are decimal notations.
How many integers between 1 and N (inclusive) have exactly K distinct digits in the hexadecimal notation without leading zeros?
Print this count modulo (10^9 + 7).

Input

Input is given from Standard Input in the following format:
N K

Here, N is in hexadecimal notation.

Output

Print the count modulo 10^9 + 7.

Constraints


- 1 \le N \lt {16}^{2 \times 10^5}
- N is given in hexadecimal notation without leading 0s.
- 1 \le K \le 16
- All values in input are integers.

Sample Input 1

10 1

Sample Output 1

15

The hexadecimal number N is 16 in decimal.
In hexadecimal, the integers between 1 and 16 are written as follows:

- 1 through 15: are 1-digit numbers in hexadecimal, containing one distinct digit.
- 16: is 10 in hexadecimal, containing two distinct digits.

Thus, there are 15 numbers that contain one distinct digit in hexadecimal.

Sample Input 2

FF 2

Sample Output 2

225

All of the 255 numbers except the following 30 numbers contain two distinct digits in hexadecimal: 1, 2, 3, \dots, \mathrm{E}, \mathrm{F}, 11, 22, 33, \dots, \mathrm{EE}, \mathrm{FF} in hexadecimal.

Sample Input 3

100 2

Sample Output 3

226

Sample Input 4

1A8FD02 4

Sample Output 4

3784674

Sample Input 5

DEADBEEFDEADBEEEEEEEEF 16

Sample Output 5

153954073

Print the count modulo (10^9 + 7).

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
