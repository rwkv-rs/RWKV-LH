Jacob enjoys flying his radio-controlled aircraft. Today, the weather is quite windy, and Jacob needs to carefully plan his flight. He has a weather forecast that provides the wind speed and direction for every second of his planned flight.

The aircraft can achieve an airspeed of up to $v_{\max}$ units per second in any direction. The wind affects the aircraft as follows: if the aircraft's airspeed is $(v_x, v_y)$ and the wind speed is $(w_x, w_y)$, then the aircraft moves by $(v_x + w_x, v_y + w_y)$ each second.

![P7069-1](https://cdn.luogu.com.cn/upload/image_hosting/2uyb1zpd.png)

Jacob has fuel for exactly $k$ seconds, and he wants to determine if the aircraft can fly from the start to the finish within this time. If possible, he needs to know the flight plan: the position of the aircraft after every second of flight.

## Input Format

The first line of the input file contains four integers $S_x, S_y, F_x, F_y$ — the coordinates of the start and finish positions ($-10000 \le S_x, S_y, F_x, F_y \le 10000$).

The second line contains three integers $n, k,$ and $v_{\max}$ — the number of wind condition changes, the duration of Jacob's flight in seconds, and the maximum airspeed of the aircraft ($1 \le n, k, v_{\max} \le 10000$).

The following $n$ lines describe the wind conditions. The $i$-th line contains three integers $t_i, w_{x_i},$ and $w_{y_i}$ — starting at time $t_i$, the wind will blow with a speed of $(w_{x_i}, w_{y_i})$ each second ($0 = t_1 < \cdots < t_i < t_{i+1} < \cdots < k; \sqrt{w_{x_i}^2 + w_{y_i}^2} \le v_{\max}$).

## Output Format

The first line should contain `Yes` if Jacob's aircraft can fly from the start to the finish within $k$ seconds, and `No` otherwise.

If it is possible, the following $k$ lines should contain the flight plan. The $i$-th line should contain two floating-point numbers $x$ and $y$ — the coordinates of the aircraft's position after $i$ seconds of flight.

The plan is considered correct if for every $1 \le i \le k$, it is possible to fly from $P_{i-1}$ to some point $Q_i$ within one second, such that the distance between $Q_i$ and $P_i$ does not exceed $10^{-5}$, where $P_0 = S$. Additionally, the distance between $P_k$ and $F$ should also not exceed $10^{-5}$.

## Sample Input and Output

### Input Sample #1

```
1 1 7 4
2 3 10
0 1 2
2 2 0
```

### Output Sample #1

```
Yes
3 2.5
5 2.5
7 4
```

## Notes/Hints

Time limit: 2 seconds, Memory limit: 256 MB.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
