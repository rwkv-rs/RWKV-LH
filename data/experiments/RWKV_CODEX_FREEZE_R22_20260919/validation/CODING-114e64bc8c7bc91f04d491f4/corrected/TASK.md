When choosing a mobile number, people often desire a number that is easy to remember and auspicious. For example, a number containing several consecutive identical digits, or one that avoids inauspicious homophonic digits. Mobile operators also consider these factors when issuing new numbers, selecting those with certain characteristics for separate sale. To facilitate early planning, operators hope to develop a tool to automatically count the number of numbers within a segment that meet these characteristics.

The tool needs to detect two features in a number: it must contain at least three consecutive identical digits; and it must not simultaneously contain both '8' and '4'. A number must include both features to be considered valid. Examples of valid numbers include: 13000988721, 23333333333, 14444101000. Examples of invalid numbers include: 1015400080, 10010012022.

A mobile number is always an 11-digit number and does not have leading zeros. The tool receives two numbers, \( L \) and \( R \), and automatically counts the number of valid numbers within the interval \([L, R]\). Both \( L \) and \( R \) are 11-digit mobile numbers.

## Input Format

The input file contains a single line with two positive integers \( L \) and \( R \) separated by a space.

## Output Format

The output file contains a single line with one integer, representing the number of valid mobile numbers.

## Sample Input and Output

### Input Sample #1

```
12121284000 12121285550
```

### Output Sample #1

```
5
```

## Notes

Sample Explanation: Valid numbers include: 12121285000, 12121285111, 12121285222, 12121285333, 12121285550.

Data Range: \( 10^{10} \leq L \leq R < 10^{11} \).

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
