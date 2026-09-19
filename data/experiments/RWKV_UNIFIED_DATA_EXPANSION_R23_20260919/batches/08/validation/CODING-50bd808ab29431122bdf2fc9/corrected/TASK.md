Arkady decides to observe a river for n consecutive days. The river's water level on each day is equal to some real value. Arkady goes to the riverside each day and makes a mark on the side of the channel at the height of the water level, but if it coincides with a mark made before, no new mark is created. The water does not wash the marks away. Arkady writes down the number of marks strictly above the water level each day, on the i -th day this value is equal to m i . Define d i as the number of marks strictly under the water level on the i -th day. You are to find out the minimum possible sum of d i over all days. There are no marks on the channel before the first day.

## Time Limit and Memory Limit

Time Limit: 1 second
Memory Limit: 256 megabytes

## Input Specification

The first line contains a single positive integer n ( 1 ≤  n  ≤ 10 5 ) — the number of days. The second line contains n space-separated integers m 1 ,  m 2 , ...,  m n ( 0 ≤  m i  <  i ) — the number of marks strictly above the water on each day.

## Output Specification

Output one single integer — the minimum possible sum of the number of marks strictly below the water level among all days.

## Examples

### Input #1
6
0 1 0 3 0 2

### Output #1
6

### Input #2
5
0 1 2 1 2

### Output #2
1

### Input #3
5
0 1 1 2 2

### Output #3
0

## Note

In the first example, the following figure shows an optimal case. Note that on day 3 , a new mark should be created because if not, there cannot be 3 marks above water on day 4 . The total number of marks underwater is 0 + 0 + 2 + 0 + 3 + 1 = 6 . In the second example, the following figure shows an optimal case.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
