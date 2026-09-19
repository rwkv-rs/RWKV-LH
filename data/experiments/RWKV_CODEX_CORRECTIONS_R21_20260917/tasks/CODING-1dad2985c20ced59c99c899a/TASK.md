Your friend Robin is a superhero. When you first found out about this, you thought, "Everyone needs a hobby, and this seems more exciting than stamp collecting," but now you are really thankful that someone is doing something about the crime in your hometown.

Every night, Robin patrols the city by jumping from roof to roof and watching what goes on below. Naturally, superheroes need to respond to crises immediately, so Robin asked you for help in figuring out how to get around your hometown quickly.

Your hometown is built on a square grid, where each block is $w \times w$ meters. Each block is filled by a single building. The buildings may have different heights. To get from one building to another (not necessarily adjacent) building, Robin makes a single jump from the center of the roof of the first building to the center of the roof of the second building. Robin cannot change direction while in the air, but can choose the angle at which to lift off.

Of course, Robin only wants to perform jumps without colliding with any buildings. Such collisions do little damage to a superhero, but building owners tend to get irritated when someone crashes through their windows. You explain the physics to Robin: "All your jumps are done with the same initial velocity $v$, which has a horizontal component $v_d$ towards the destination and vertical component $v_h$ upwards, so $v_d^2 + v_h^2 = v^2$. As you travel, your horizontal velocity stays constant $(v_d(t) = v_d)$, but your vertical velocity is affected by gravity $(v_h(t) = v_h - t \cdot g)$, where $g = 9.80665 \, m/s^2$ in your hometown. Naturally, your cape allows you to ignore the effects of air resistance. This allows you to determine your flight path and..." At which point you notice that Robin has nodded off - less math, more super-heroing!

So it falls to you: given a layout of the city and the location of Robin's secret hideout, you need to determine which building roofs Robin can reach, and the minimum number of jumps it takes to get to each roof.

Note that if Robin's jump passes over the corner of a building (where four buildings meet), then the jump needs to be higher than all four adjacent buildings.

## Input Format

The input starts with a line containing six integers $d_x$, $d_y$, $w$, $v$, $ℓ_x$, $ℓ_y$. These represent the size $d_x \times d_y$ of the city grid $(1 \le d_x, d_y \le 20)$ in blocks, the width of each building $(1 \le w \le 10^3)$ in meters, Robin's takeoff velocity $(1 \le v \le 10^3)$ in meters per second, and the coordinates $(ℓ_x, ℓ_y)$ of Robin's secret hideout $(1 \le ℓ_x \le d_x, 1 \le ℓ_y \le d_y)$.

The first line is followed by a description of the heights of the buildings in the city grid. The description consists of $d_y$ lines, each containing $d_x$ non-negative integers. The $j$-th line contains the heights for buildings $(1, j), (2, j), \ldots, (d_x, j)$. All heights are given in meters and are at most $10^3$.

## Output Format

Display the minimum number of jumps Robin needs to get from the secret hideout to the roof of each building. If there is no way to reach a building's roof, display $X$ instead of the number of jumps. Display the buildings in the same order as given in the input file, split into $d_y$ lines, each containing $d_x$ values.

## Sample Input and Output

### Input Sample #1

```
4 1 100 55 1 1
10 40 60 10
```

### Output Sample #1

```
0 1 1 1
```

### Input Sample #2

```
4 4 100 55 1 1
0 10 20 30
10 20 30 40
20 30 200 50
30 40 50 60
```

### Output Sample #2

```
0 1 1 2
1 1 1 2
1 1 X 2
2 2 2 3
```

## Notes/Hints

Time limit: 2 seconds, Memory limit: 1024 MB.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
