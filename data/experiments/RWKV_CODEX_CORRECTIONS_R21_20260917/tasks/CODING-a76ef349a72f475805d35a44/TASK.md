Ingrid is the head of a large railway station and, among other duties, is responsible for routing trains to the correct platforms. The station has one entrance, and there are many switches that direct trains to other switches and platforms.

Each switch has one inbound track and two outbound tracks, platforms have one inbound track, and the station entrance has one outbound track. Each outbound track is connected to one inbound track and vice versa. Every switch and platform is reachable from the station entrance.

Platforms have a rail dead end, and you may assume that trains disappear from the platform immediately after arriving.

Each morning, Ingrid looks at the timetable and writes switch toggling instructions: when and which switch to toggle. She would like to automate this process to save a lot of time.

## Input Format

The first line of the input file contains a single integer \( n \) — the total number of switches and platforms on the station \( (3 \le n \le 51) \).

The \( i \)-th of the following \( n \) lines describes a switch or a platform with an index \( i \). The description starts with a character `p` for a platform or `s` for a switch. The next number \( q_i \) indicates the number of the switch the inbound track is connected to, or \( 0 \) if it is connected to the station entrance \( (0 \le q_i < i) \). The description of the platform also contains a unique lowercase English letter — the platform identifier.

Trains spend exactly one minute to move between two connected switches or a switch and a platform. In the morning, each switch is toggled in a way that a train would pass to the one of the two outbound tracks connected to the switch/platform with the lower number.

The next line of the input file contains a single integer \( m \) \( (1 \le m \le 1000) \) — the number of trains in the timetable.

Each of the following \( m \) lines contains an integer \( a_i \) \( (0 \le a_i \le 10000; a_i > a_{i-1}) \) — the time in minutes when a train arrives at the station entrance, and the letter \( p_i \) — the identifier of the destination platform for this train.

## Output Format

In the first line, output an integer \( c \) — the number of commands in the switch toggling instruction. For each command, output two integers \( s_i \) and \( t_i \) \( (1 \le s_i \le n; 0 \le t_i \le 10^9) \) — the number of the switch and the time to toggle it. Assume that the switch is toggled between minutes \( t_i - 1 \) and \( t_i \).

Output commands in order of non-decreasing time. The number of commands should not exceed \( 100,000 \).

## Sample Input and Output

### Input Sample #1

```
7
s 0
s 1
s 1
p 2 a
p 2 b
p 3 c
p 3 d
5
0 a
1 c
3 b
4 a
5 d
```

### Output Sample #1

```
6
1 2
1 4
2 4
2 6
1 6
3 7
```

### Input Sample #2

```
5
s 0
p 1 y
s 1
p 3 z
p 3 x
3
7 y
8 y
15 y
```

### Output Sample #2

```
0
```

### Input Sample #3

```
3
s 0
p 1 y
p 1 z
3
7 y
8 y
10 y
```

### Output Sample #3

```
5
1 1
1 2
1 2
1 3
1 200
```

## Notes/Hints

Below is the time trace for the first example.

Time limit: 2 seconds, Memory limit: 256 MB.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
