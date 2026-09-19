The company DoD has determined when scanning robots will collide. Robots will be launched simultaneously from a "magic gun" between two horizontal lanes. They move in a straight line unless they hit a wall or another robot (i.e., two robots appear at the same place at the same time).  
Whenever a robot hits a wall, it will bounce back without losing speed. After bouncing, it continues to move in a straight line (*the angle of incidence equals the angle of reflection*).  
When robots collide, they "crash" (this word also means collision, you can understand it as a very intense impact).  
You need to write a program to determine whether and when the robots will "crash." To simplify the physics problem and computer model, we assume:  
* The horizontal lane exists in a 2D plane and extends to the left and right; the walls are straight lines.  
* Each robot is a point mass (Robot: I'm just a point mass???), which means its volume is zero.  
* The robots will maintain their initial launch speed until they "crash" with another robot or are launched by the "magic gun" again.  
* There are only two "magic guns," one installed to the left of the other, and both are mounted on the horizontal lane. The initial firing angle of the left gun is between -85° and 85°, while the right gun's initial firing angle is between 95° and 180° or -95° and 180° (all angles are counterclockwise relative to the x-axis).
* Robots that appear at the same place within 0.5s of each other will "crash."  
* The horizontal lane is 10 units high, for every pair (x,y) on the lane, (0<=y<=10).  
* The speed of the robots is positive.

## Input and Output Example

### Input Example #1

```
0 4 0 3.3
40 5 125 5
1 6 -5 10
5 2 95 20
2 5 45 5
42 5 -135 5
0 6 20 3
0 5 180 4
```

### Output Example #1

```
Robot Problem #1: Robots do not collide.
Robot Problem #2: Robots collide at (4.68,5.68)
Robot Problem #3: Robots collide at (22.00,5.00)
Robot Problem #4: Robots do not collide.
```
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
