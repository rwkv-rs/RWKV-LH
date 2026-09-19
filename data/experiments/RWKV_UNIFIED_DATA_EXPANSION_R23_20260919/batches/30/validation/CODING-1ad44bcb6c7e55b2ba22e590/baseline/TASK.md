"ABEAS Corp." is a very small company that owns a single airplane. The customers of ABEAS Corp are large airline companies which rent the airplane to accommodate occasional overcapacity.

Customers send renting orders that consist of a time interval and a price that the customer is ready to pay for renting the airplane during the given time period. Orders of all the customers are known in advance. Of course, not all orders can be accommodated and some orders have to be declined. Eugene LAWLER, the Chief Scientific Officer of ABEAS Corp would like to maximize the profit of the company.

You are requested to compute an optimal solution.

   
#### Small Example

 Consider for instance the case where the company has 4 orders:

- Order 1 (start time 0, duration 5, price 10)
- Order 2 (start time 3, duration 7, price 8)
- Order 3 (start time 5, duration 9, price 7)
- Order 4 (start time 6, duration 9, price 8)

 The optimal solution consists in declining Order 2 and 3 and the gain is 10+8 = 18.  
 Note that the solution made of Order 1 and 3 is feasible (the airplane is rented with no interruption from time 0 to time 14) but non-optimal.

## Input Format

The first line of the input contains a number T

## Output Format

You are required to compute an optimal solution. For each test case your program has to write the total price paid by the airlines.

## Sample Input and Output

### Sample Input #1

```
1
4
0 5 10
3 7 14
5 9 7
6 9 8
```

### Sample Output #1

```
18
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
