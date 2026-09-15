AtCoder's office is divided into an $ R \times C $ grid ($ R $ rows and $ C $ columns), where each cell can either contain an employee's desk, a server rack, or be an empty space.  
 In a region of AtCoder, winter is cold, and to save on heating costs, it was decided to only enclose the necessary spaces in the office.  
 However, due to material constraints, the enclosed area must be a rectangular region parallel to the grid lines.  
 Therefore,

- Immediately above the topmost row with a desk or server rack,
- Immediately below the bottommost row with a desk or server rack,
- Immediately left of the leftmost column with a desk or server rack,
- Immediately right of the rightmost column with a desk or server rack

These four boundaries were enclosed with walls.  
 The enclosed area became an $ X \times Y $ grid ($ X $ rows and $ Y $ columns).  
 Additionally, the office contains $ D $ desks and $ L $ server racks.  
 Write a program to determine the number of possible patterns for the arrangement of desks and server racks in the office, modulo $ 1000000007 = 10^9+7 $.  
 The input is given from the standard input in the following format: > $ R $ $ C $ $ X $ $ Y $ $ D $ $ L $

1. The first line contains integers $ R, C (1 ≦ R, C ≦ 30) $ representing the number of rows and columns in the office grid, separated by spaces.
2. The second line contains integers $ X, Y (1 ≦ X ≦ R, 1 ≦ Y ≦ C) $ representing the number of rows and columns in the enclosed area, separated by spaces.
3. The third line contains integers $ D, L (D, L ≧ 0, 1 ≦ D+L ≦ X \times Y) $ representing the number of desks and server racks in the office, separated by spaces.

Output the number of possible patterns for the arrangement of desks and server racks in the office, modulo $ 1000000007 = 10^9+7 $, on a single line.  
Ensure a newline at the end of the output. If you correctly solve all test cases where $ D+L = X \times Y $, you will receive $ 100 $ out of $ 101 $ points.  
The full solution is very difficult, so consider starting by securing partial points.

```
<pre class="prettyprint linenums">
3 2
2 2
2 2
```

```
<pre class="prettyprint linenums">
12
```

- This case satisfies $ D+L=X \times Y $ and may be included in the partial points test cases.
- There are $ 12 $ possible arrangements, where `D` is a desk, `L` is a server rack, and `.` is an empty space.

```
DD  DL  DL  LD  LD  LL  ..  ..  ..  ..  ..  ..
LL  DL  LD  DL  LD  DD  DD  DL  DL  LD  LD  LL
..  ..  ..  ..  ..  ..  LL  DL  LD  DL  LD  DD
```

```
<pre class="prettyprint linenums">
4 5
3 1
3 0
```

```
<pre class="prettyprint linenums">
10
```

- This case satisfies $ D+L=X \times Y $ and may be included in the partial points test cases.

```
<pre class="prettyprint linenums">
23 18
15 13
100 95
```

```
<pre class="prettyprint linenums">
364527243
```

- This case satisfies $ D+L=X \times Y $ and may be included in the partial points test cases.
- The number of office layout patterns is $ 145180660592914517790287604376765671109248284280228061640640 $, and you should output the remainder when divided by $ 10^9+7 $, which is $ 364527243 $.

```
<pre class="prettyprint linenums">
30 30
24 22
145 132
```

```
<pre class="prettyprint linenums">
976668549
```

- This case does not satisfy $ D+L=X \times Y $ and will not be included in the partial points test cases.
- Do not force a solution; only attempt if you have spare capacity.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
