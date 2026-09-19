Simulate a series of scenarios where two trains, one departing from the metro center hub and the other departing from the outermost station on the same route, approach each other along the route. Transportation planners want to know when and where these two trains will meet. You need to write a program to determine these outcomes.

This train travel scenario needs to be simplified and is based on the following assumptions:

1. All trains stop at each station for a fixed duration.
2. All trains accelerate and decelerate at the same constant rate and have the same maximum possible speed.
3. When a train leaves a station, it accelerates (at a constant rate) until it reaches maximum speed. It maintains this maximum speed until it begins to decelerate (at the same constant rate) as it approaches the next station. Trains depart from stations with an initial speed of zero (0.0) and arrive at end stations with a terminal speed of zero. The adjacent stations on each route are far enough apart to allow the train to accelerate to its maximum speed before it begins to decelerate.
4. In each scenario, both trains depart simultaneously.
5. Any route has a maximum of 31 stations.
6. The meeting time of the two trains will never occur just as one train leaves a station.

### Input

All input values are real numbers. The data for each scenario is formatted as follows.

$d_{1}$ $d_{2}$ ... $d_{n}$ 0.0 for a single route, indicates a list of distances from each station to the metro center hub (in miles - each mile has 5280 feet), separated by one or more spaces. The stations are listed in ascending order, starting from the station closest to the metro center hub (station 1), and continuing to the outermost station. All distances are greater than zero. The list is terminated by the sentinel value 0.0.

v is the maximum train speed in feet per minute.

s is the constant train acceleration in feet/minute².

m is the number of minutes the train stops at each station.

The data set is terminated by the number "-1.0".

### Output

For each scenario, output the following marked data.

1. Scenario number (consecutively numbered starting from scenario #1).
2. The meeting time of the two trains, in minutes, from the departure time. All times must be shown to one decimal place. Additionally, if the trains meet at a station, output the station number where they meet.
3. The distance from the metro center hub to the meeting point, in miles. The distance must be shown to three decimal places.

Print a blank line between consecutive test cases.

## Input and Output Example

### Input Example #1

```
15.0 0.0
5280.0
10560.0
5.0
3.5 7.0 0.0
5280.0
10560.0
2.0
3.4 7.0 0.0
5280.0
10560.0
2.0
-1.0
```

### Output Example #1

```
Scenario #1:
Meeting time: 7.8 minutes
Meeting distance: 7.500 miles from metro center hub
Scenario #2:
Meeting time: 4.0 minutes
Meeting distance: 3.500 miles from metro center hub, in station 1
Scenario #3:
Meeting time: 4.1 minutes
Meeting distance: 3.400 miles from metro center hub, in station 1
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
