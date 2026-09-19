As is well known, Michael Schumacher is the greatest king of the racing world. From 1991 to 2006, he participated in over 260 races, winning nearly 100 race victories and 9 championship titles. Schumacher's remarkable achievements are largely due to his exceptionally talented advisory team. Before each race, his team would formulate strategies for him based on the track, weather, road conditions, and the status of his car.

## Problem Description

In F1 races, if all other parameters of the car are the same, the speed of the car mainly depends on its fuel load. Too much fuel reduces the car's speed and increases fuel consumption; too little fuel requires more pit stops for refueling. Therefore, a key task for the advisory team is to determine the initial fuel load and the refueling strategy for Schumacher before each race, to minimize the total time to complete the race.

As the chief programmer of the advisory team, Dr. Liu's task is to write a program that determines the initial fuel load and the refueling strategy for Schumacher before the race.

## Input Format

The input data includes the following numbers:

- The total number of laps in the race (a positive integer not exceeding 1)
- The time required for an empty car (with no fuel) to complete one lap theoretically (a floating-point number in seconds)
- The additional time per liter of fuel added that increases the time to complete one lap (a floating-point number in seconds)
- The fuel consumption of an empty car to complete one lap theoretically (a floating-point number in liters)
- The additional fuel consumption per liter of fuel added that increases the fuel consumption per lap (a floating-point number in liters, strictly less than 1)
- The time required for each pit stop (a floating-point number in seconds, excluding the time needed for refueling, which is determined by the next input parameter)
- The time required to add each liter of fuel during a pit stop (a floating-point number in seconds)

We always consider a complete lap as a unit. The change in fuel during the process of running one lap is not considered. Refueling can only be done after completing a lap.

## Output Format

- The first line includes three numbers:
  1. The shortest total time required for Schumacher's car to complete all laps (a floating-point number, rounded to three decimal places)
  2. The initial fuel load of Schumacher's car before the race (a floating-point number, rounded to three decimal places)
  3. The number of pit stops \( m \) during the race (an integer)

- The next \( m \) lines, each including two numbers:
  1. The number of laps completed before the \( i \)-th pit stop (an integer)
  2. The amount of fuel added during the \( i \)-th pit stop (a floating-point number, rounded to three decimal places)

## Sample Input and Output

### Input Sample #1

```
3 100 0 10 0 20 0
```

### Output Sample #1

```
300.000 30.000 0
```

### Input Sample #2

```
3 100 2 10 0.1 20 1
```

### Output Sample #2

```
422.469 23.457 1
2 11.111
```

### Input Sample #3

```
3 100 4 10 0 20 1
```

### Output Sample #3

```
480.000 10.000 2
1 10.000
2 10.000
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
