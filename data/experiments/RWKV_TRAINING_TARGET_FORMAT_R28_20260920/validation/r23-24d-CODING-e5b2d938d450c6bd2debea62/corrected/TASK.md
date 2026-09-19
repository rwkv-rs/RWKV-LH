NOI2130 is about to commence. To enhance the viewing experience, CCF has decided to evaluate each contestant's score one by one and broadcast the live award cutoff score. The award rate for this competition is \( w\% \), meaning the minimum score among the top \( w\% \) contestants is the live cutoff score.

More specifically, if \( p \) contestants' scores have been evaluated so far, the planned number of awardees is \( \max(1, \lfloor p \times w\% \rfloor) \), where \( w \) is the award percentage, \( \lfloor x \rfloor \) denotes the floor function of \( x \), and \( \max(x, y) \) represents the larger number between \( x \) and \( y \). If there are contestants with the same score, all such contestants will be awarded, potentially increasing the actual number of awardees beyond the planned number.

As a technical staff member of the evaluation team, please help CCF write a live broadcast program.

## Input Format

The first line contains two integers \( n \) and \( w \), representing the total number of contestants and the award rate, respectively.  
The second line contains \( n \) integers, representing the scores of the contestants evaluated one by one.

## Output Format

Output a single line containing \( n \) non-negative integers, representing the live award cutoff scores as each contestant's score is announced. Separate adjacent integers with a space.

## Sample Input and Output

### Sample Input #1

```
10 60
200 300 400 500 600 600 0 300 200 100
```

### Sample Output #1

```
200 300 400 400 400 500 400 400 300 300
```

### Sample Input #2

```
10 30
100 100 600 100 100 100 100 100 100 100
```

### Sample Output #2

```
100 100 600 600 600 600 100 100 100 100
```

## Notes

### Sample 1 Explanation

![Explanation Image](https://cdn.luogu.com.cn/upload/image_hosting/l453vhow.png)

### Data Size and Constraints

The values of \( n \) for each test case are as follows:

| Test Case Number | \( n \) |
| :--: | :--: |
| \( 1 \sim 3 \) | \( 10 \) |
| \( 4 \sim 6 \) | \( 500 \) |
| \( 7 \sim 10 \) | \( 2000 \) |
| \( 11 \sim 17 \) | \( 10^4 \) |
| \( 18 \sim 20 \) | \( 10^5 \) |

For all test cases, each contestant's score is a non-negative integer not exceeding \( 600 \), and the award percentage \( w \) is a positive integer where \( 1 \le w \le 99 \).

### Hints

When calculating the planned number of awardees, if you use floating-point variables (such as `float`, `double` in C/C++, or `real`, `double`, `extended` in Pascal) to store the award percentage \( w\% \), the result of \( 5 \times 60\% \) might be \( 3.000001 \) or \( 2.999999 \), leading to an uncertain result after flooring. Therefore, it is recommended to use only integer variables to ensure accurate calculations.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
