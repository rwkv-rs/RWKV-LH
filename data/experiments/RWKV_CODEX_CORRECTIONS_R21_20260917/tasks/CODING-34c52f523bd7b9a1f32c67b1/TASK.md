For simplicity in calculations, astronomers use the Julian day to express time. The Julian day is defined as the number of days that have elapsed since **noon on January 1, 4713 BC** to a certain moment, with fractions of a day expressed as decimals. This astronomical calendar system maps every moment uniformly onto a number line, facilitating the calculation of time differences.

Given a Julian day without fractional parts, please calculate the corresponding Gregorian calendar date for that Julian day, which is always at noon.

The current Gregorian calendar, introduced by Pope Gregory XIII in 1582, is an amendment to the original Julian calendar (note: the Julian calendar is not directly related to the Julian day). Specifically, the Gregorian calendar dates are calculated according to the following rules:

1. From October 15, 1582 AD onwards: Use the Gregorian calendar, where January, March, May, July, August, October, and December have 31 days; April, June, September, and November have 30 days; February has 28 days in a common year and 29 days in a leap year. A year is a leap year if it is a multiple of 400, or if it is a multiple of 4 but not a multiple of 100.
2. From October 5 to October 14, 1582 AD: These dates do not exist; October 4, 1582 AD is followed by October 15, 1582 AD.
3. Before October 4, 1582 AD: Use the Julian calendar, where the months have the same number of days as in the Gregorian calendar, but every year that is a multiple of 4 is a leap year.
4. Although the Julian calendar was officially implemented in 45 BC and underwent several adjustments, today's practice is to retroactively apply the final rules of the Julian calendar to all dates before October 4, 1582 AD. Note that there is no year zero, meaning that the year following 1 BC is 1 AD. Therefore, years like 1 BC, 5 BC, 9 BC, 13 BC, etc., are considered leap years.

## Input Format

The first line contains an integer \( Q \), representing the number of queries.  
The next \( Q \) lines each contain a non-negative integer \( r_i \), representing a Julian day.

## Output Format

For each Julian day \( r_i \), output a line representing the date string \( s_i \). There will be \( Q \) lines in total. The format of \( s_i \) is as follows:

1. If the year is AD, the format is `Day Month Year`. Day, Month, and Year are all non-leading zero integers, separated by a space. For example: Noon on November 7, 2020 AD, the output is `7 11 2020`.
2. If the year is BC, the format is `Day Month Year BC`. The Year is the numerical value of the year, with the rest being the same as for AD. For example: Noon on February 1, 841 BC, the output is `1 2 841 BC`.

## Sample Input and Output

### Input Sample #1

```
3
10
100
1000
```

### Output Sample #1

```
11 1 4713 BC
10 4 4713 BC
27 9 4711 BC
```

### Input Sample #2

```
3
2000000
3000000
4000000
```

### Output Sample #2

```
14 9 763
15 8 3501
12 7 6239
```

### Input Sample #3

```
See the attached file julian/julian3.in
```

### Output Sample #3

```
See the attached file julian/julian3.ans
```

## Notes

**[Data Range]**

| Test Point Number | \( Q = \) | \( r_i \le \) |
|:-:|:-:|:-:|
| 1 | 1000 | 365 |
| 2 | 1000 | 10^4 |
| 3 | 1000 | 10^5 |
| 4 | 10000 | 3 × 10^5 |
| 5 | 10000 | 2.5 × 10^6 |
| 6 | 10^5 | 2.5 × 10^6 |
| 7 | 10^5 | 5 × 10^6 |
| 8 | 10^5 | 10^7 |
| 9 | 10^5 | 10^9 |
| 10 | 10^5 | Year answer does not exceed 10^9 |

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
