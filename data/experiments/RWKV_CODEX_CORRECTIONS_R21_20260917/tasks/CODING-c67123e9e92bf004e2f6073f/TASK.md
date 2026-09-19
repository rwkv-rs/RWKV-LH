Do you like traffic lights? Encountering a series of green lights on your way to work can be delightful. One day, as you're driving on a straight road, you suddenly notice all the traffic lights simultaneously turning from red to green. This sparks a question in your mind: how long will it take for all the lights to be green again (starting from the moment they all simultaneously turned green)? Here, it is not required for all the lights to switch simultaneously from red to green, but rather that at some second, all the lights are green at the same time. "Next time" means after at least one traffic light has turned red.

Given the cycle time of each traffic light, your task is to calculate when they will all be green again at the same time.

### Input

The input consists of multiple test cases. Each test case is a sequence of integers separated by one or more spaces (possible across multiple lines, but each line will not exceed 100 characters), representing the cycle time of each traffic light in seconds. The explanation is as follows: if the cycle time is 25, it means the light is green (and yellow) for 25 seconds and red for 25 seconds. The yellow light duration is always 5 seconds, so in this example, the green light duration is actually only 20 seconds. The cycle times are between 10 and 90 seconds, and there are at least 2 traffic lights and at most 100. A cycle time of 0 indicates the end of a test case. A line containing only three consecutive zeros indicates the end of the input. Refer to the sample input for clarification.

### Output

For each test case, output a single line as specified, referring to the sample output for the format. If the time exceeds 5 hours, output: "Signals fail to synchronise in 5 hours."

## Sample Input / Output

### Sample Input #1

```
19 20 0
30
25 35 0
0 0 0
```

### Sample Output #1

```
00:00:40
00:05:00
```
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
