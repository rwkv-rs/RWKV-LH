### Problem
Gondwanaland Telecom charges phone calls based on the time of day and the distance of the call. The table below outlines the basic call rate plan, with charge bands arranged according to call distance.

![Rate Chart](https://cdn.luogu.org/upload/vjudge_pic/UVA145/c3d07da6ed463d6c9b36c009da90a023dd9fb9c8.png)

All charges are accumulated based on the number of minutes the call lasts. If a call spans two time segments, charges are calculated based on the time spent in each segment and their respective rates. For example, a call that starts at 5:58 PM and ends at 6:04 PM is charged as 2 minutes at the daytime rate and 4 minutes at the nighttime rate. Calls lasting less than 1 minute are not charged, and the longest call can be up to 24 hours. Write a program to read all call information and calculate the respective charges.

### Input and Output
The input consists of multiple lines, each containing: charge band (a capital letter from "A" to "E"), the called number (a 7-digit string separated by dashes), the start time and the end time of the call. Each piece of data is separated by a space. Time is given in the 24-hour format with hours and minutes separated by a space, each number having two digits (note: use leading zeros for single-digit numbers). A single line containing only a "#" indicates the end of input.

Each output line must include the called number, the number of minutes in each charge band, the charge band letter, and the total charges. Output should be formatted as follows.

### Sample Input
```
A 183-5724 17 58 18 04
#
```

### Sample Output
```
183-5724 2 4 0 A 0.44
```
```
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
