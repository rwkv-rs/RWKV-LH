There are $n$ consecutive seat places in a railway carriage. Each place is either empty or occupied by a passenger. The university team for the Olympiad consists of $a$ student-programmers and $b$ student-athletes. Determine the largest number of students from all $a+b$ students, which you can put in the railway carriage so that: no student-programmer is sitting next to the student-programmer;  and no student-athlete is sitting next to the student-athlete. In the other words, there should not be two consecutive (adjacent) places where two student-athletes or two student-programmers are sitting. Consider that initially occupied seat places are occupied by jury members (who obviously are not students at all).

## Time Limit and Memory Limit

Time Limit: 2 seconds
Memory Limit: 256 megabytes

## Input Specification

The first line contain three integers $n$, $a$ and $b$ ($1 \le n \le 2\cdot10^{5}$, $0 \le a, b \le 2\cdot10^{5}$, $a + b > 0$) — total number of seat places in the railway carriage, the number of student-programmers and the number of student-athletes. The second line contains a string with length $n$, consisting of characters " . " and " * ". The dot means that the corresponding place is empty. The asterisk means that the corresponding place is occupied by the jury member.

## Output Specification

Print the largest number of students, which you can put in the railway carriage so that no student-programmer is sitting next to a student-programmer and no student-athlete is sitting next to a student-athlete.

## Examples

### Input #1
5 1 1
*...*

### Output #1
2

### Input #2
6 2 3
*...*.

### Output #2
4

### Input #3
11 3 10
.*....**.*.

### Output #3
7

### Input #4
3 2 3
***

### Output #4
0

## Note

In the first example you can put all student, for example, in the following way: *.AB* In the second example you can put four students, for example, in the following way: *BAB*B In the third example you can put seven students, for example, in the following way: B*ABAB**A*B The letter A means a student-programmer, and the letter B — student-athlete.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
