You are the God of Wind.

By moving a big cloud around, you can decide the weather: it invariably rains under the cloud, and the sun shines everywhere else.

But you are a benign God: your goal is to give enough rain to every field in the countryside, and sun to markets and festivals. Small humans, in their poor vocabulary, only describe this as “weather forecast”.

You are in charge of a small country, called Paccimc. This country is constituted of 4 × 4 square areas, denoted by their numbers.

<image>

Your cloud is of size 2 × 2, and may not cross the borders of the country.

You are given the schedule of markets and festivals in each area for a period of time.

On the first day of the period, it is raining in the central areas (6-7-10-11), independently of the schedule.

On each of the following days, you may move your cloud by 1 or 2 squares in one of the four cardinal directions (North, West, South, and East), or leave it in the same position. Diagonal moves are not allowed. All moves occur at the beginning of the day.

You should not leave an area without rain for a full week (that is, you are allowed at most 6 consecutive days without rain). You don’t have to care about rain on days outside the period you were given: i.e. you can assume it rains on the whole country the day before the period, and the day after it finishes.
Input

The input is a sequence of data sets, followed by a terminating line containing only a zero.

A data set gives the number N of days (no more than 365) in the period on a single line, followed by N lines giving the schedule for markets and festivals. The i-th line gives the schedule for the i-th day. It is composed of 16 numbers, either 0 or 1, 0 standing for a normal day, and 1 a market or festival day. The numbers are separated by one or more spaces.

Output

The answer is a 0 or 1 on a single line for each data set, 1 if you can satisfy everybody, 0 if there is no way to do it.

Example

Input

1
0 0 0 0 0 1 0 0 0 0 0 0 0 0 0 0
7
0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
1 0 0 0 0 0 1 0 0 0 0 1 1 0 0 1
0 0 0 0 0 0 0 0 1 0 0 0 0 1 0 1
0 0 0 0 0 0 0 0 0 1 0 1 0 0 0 0
0 1 0 1 0 0 0 0 0 0 0 0 0 0 0 0
1 0 0 1 0 0 0 0 0 0 0 0 0 0 0 1
0 0 0 0 0 1 0 0 1 0 0 0 0 0 0 0
7
0 0 0 0 0 0 0 0 1 0 0 0 0 0 0 0
0 0 1 0 0 0 0 1 0 0 0 0 0 1 0 0
0 0 0 1 0 0 0 0 0 0 1 0 1 0 0 0
0 1 0 0 0 0 0 1 0 0 0 0 1 0 0 0
0 0 0 0 0 0 0 0 1 0 0 0 0 0 0 0
0 0 0 0 0 0 0 1 1 0 1 0 0 0 0 1
0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 0
15
0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0
0 0 0 0 0 0 0 0 1 0 0 0 0 0 0 0
0 0 0 0 0 0 0 0 1 1 0 0 0 0 0 0
0 0 0 0 0 0 0 0 1 0 0 0 0 0 0 0
0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
0 0 0 0 0 0 0 0 1 1 0 1 0 0 0 0
0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0
0 0 1 1 0 0 0 0 0 1 0 0 0 0 0 0
1 1 0 0 0 0 0 0 0 0 1 0 0 1 0 0
0 0 0 0 0 1 0 0 0 0 0 1 0 0 0 0
0 0 1 0 0 0 0 0 0 0 0 0 0 0 1 0
1 0 0 1 1 0 0 0 0 1 0 1 0 0 0 0
0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0
0 0 0 0 0 1 0 1 0 1 0 0 0 0 0 0
0


Output

0
1
0
1

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
