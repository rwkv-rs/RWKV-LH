It's winter of 2017. (Once again, it's the season of white albums, lol)

![Skiing Kotori](https://db.loveliv.es/png/navi/476/0)

After skiing, Kotori suddenly craves for some snacks! So she heads to the dessert shop.

Winter in Japan often brings heavy snow. Unfortunately, today is one of those days, with the snow depth increasing by \( q \) millimeters every second.

Akiba has \( n \) locations, numbered from 1 to \( n \). Each location initially has a snow height of \( h_i \).

There are \( m \) **bidirectional** roads connecting these locations, with lengths \( w_i \) meters.

Due to the heavy snow, public transportation has ceased, so Kotori has to walk home. Her walking speed is 1 meter per second.

For the convenience of map drawing, Akiba's road planning ensures that each road strictly connects two different locations and no two roads connect the same pair of locations.

Each location has a limit snow height \( l_i \), in millimeters. If the snow height at a location exceeds \( l_i \), Kotori will be trapped and unable to reach her home.

The dessert shop is located at location \( s \), and Kotori's home is at location \( t \).

The snow at the dessert shop and Kotori's home is not considered.

Kotori wants to get home within \( g \) seconds to enjoy her snack, as quickly as possible. If she cannot reach home within \( g \) seconds or gets trapped along the way, Kotori will turn wtnap into her snack ( ・ 8 ・ )

## Input Format

The first line contains six integers separated by spaces: \( n \), \( m \), \( s \), \( t \), \( g \), and \( q \).

The following \( n \) lines each contain two integers separated by spaces, representing the initial snow height \( h_i \) and the limit snow height \( l_i \) of each location.

The next \( m \) lines each contain three integers separated by spaces, representing the two locations \( u \) and \( v \) connected by a road and the length \( w_i \) of that road.

## Output Format

Output a single integer on one line, representing the shortest time to reach Kotori's home.

If wtnap becomes Kotori's snack, output "wtnap wa kotori no oyatsu desu!"

Do not include quotes in the output.

## Sample Input and Output

### Input Sample #1

```
2 1 1 2 10 1
1 10
3 10
1 2 6
```

### Output Sample #1

```
6
```

### Input Sample #2

```
5 6 2 5 10 1
1 10
1 10
1 10
1 10
1 10
1 5 9
1 3 9
2 4 1
2 5 9
3 4 1
3 5 6
```

### Output Sample #2

```
8
```

### Input Sample #3

```
5 6 2 5 10 1
1 10
1 10
10 10
1 10
1 10
1 5 9
1 3 9
2 4 1
2 5 11
3 4 1
3 5 6
```

### Output Sample #3

```
wtnap wa kotori no oyatsu desu!
```

## Notes/Hints

For 0% of the data, it is exactly the same as the first sample;
For 40% of the data, \( q = 0 \).
For 50% of the data in the previous line, all \( w_i < l_i \).
For 100% of the data, \( 1 \leq s, t \leq n \); \( 0 \leq g, q \leq 10^9 \); \( 0 \leq w_i \leq l_i \leq 10^9 \).

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
