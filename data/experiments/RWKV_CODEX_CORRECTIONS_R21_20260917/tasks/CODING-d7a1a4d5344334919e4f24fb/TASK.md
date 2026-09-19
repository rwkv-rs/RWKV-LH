In 1858, Scottish antiquarian A. Henry Rhind obtained a document now known as the "Rhind Papyrus" titled "Directions for Attaining Knowledge into All Obscure Secrets," which provided significant insights into how ancient Egyptians performed arithmetic.

In this numeral system, **there is no zero**. There are separate characters to represent one, ten, hundred, thousand, ten thousand, one hundred thousand, one million, and ten million. To solve this problem, we use approximately ASCII equivalent symbols:

- `|` represents one (note, this is a **line**, not 1)
- `n` represents ten
- `9` represents one hundred
- `8` represents one thousand
- `r` represents ten thousand

(True Egyptian hieroglyphs are more pictorial but follow the overall shape of these modern symbols. For this problem, we will not consider numbers greater than **99,999**.)

Numbers are written as a set of digits: one, followed by tens, hundreds, thousands, and ten thousands. Therefore, our number 4023 would be presented as: `||| nnnn 8888`. Note that zero positions are represented by a group containing no corresponding symbols. Hence, the number 40,230 is presented as: `nnnnn 9 rrrr`. (In the Rhind Papyrus, groups were drawn more vividly, often spread across multiple horizontal lines; but for this problem, you should write all numbers on one line.)

To multiply two numbers `a` and `b`, the Egyptians used two columns of numbers. They started by writing the number `|` (as a symbol here) next to the number `a` in the left column. They then formed new rows by doubling the numbers in both columns. Note that if any group of symbols exceeds nine (here, numbers), doubling can be achieved by copying the symbol and normalizing through a carrying process. Doubling continues as long as the number in the left column does not exceed the other multiplicand `b`. Numbers in the first column, which sum to the multiplicand `b`, are marked with an asterisk. Then the numbers in the right column next to the asterisked numbers are summed up to produce the result.

Below, we demonstrate the corresponding steps for multiplying 483 by 27:

![](https://cdn.luogu.com.cn/upload/image_hosting/kuqvbz5x.png)
![](https://cdn.luogu.com.cn/upload/image_hosting/nv3bxmv5.png)

(The solution is produced by adding together:

![](https://cdn.luogu.com.cn/upload/image_hosting/z5flgifc.png)

You are to write a program to execute this Egyptian multiplication.

### Input

The input will consist of several pairs of non-zero numbers written in the Egyptian system as described above. Each line will contain one number; each number will consist of symbol groups, each group ending with a space (including the last group). The input ends with an empty line.

### Output

For each pair of numbers, your program should print the steps used in Egyptian multiplication as shown above. Numbers in the left column should be left-aligned. Each number in both columns will be represented by symbol groups, each ending with a single space (including the last group). If there is an asterisk in the left column, it should be separated from the end of the left number by one space. Space should fill up to the 34th character position. Numbers in the right column should start from the 35th character position of that line and end with a newline.

The test data will be chosen to ensure no overlaps occur. After displaying each doubling step, your program should print the string: "The solution is:", followed by the product of the two numbers in Egyptian symbols (modulo 100000).

### Sample Input
```c
||
||
|||
||||
nnnnnn 9
||| n
n
9
|||
8
```

### Sample Output
```c
|                                ||
|| *                             ||||
The solution is: ||||
|                                |||
||                               ||||||
|||| *                           || n
The solution is: || n
| *                              nnnnnn 9
||                               nn 999
|||| *                           nnnn 999999
|||||||| *                       nnnnnnnn 99 8
The solution is: nnnnnnnn 88
|                                n
||                               nn
|||| *                           nnnn
||||||||                         nnnnnnnn
|||||| n                         nnnnnn 9
|| nnn *                         nn 999
|||| nnnnnn *                    nnnn 999999
The solution is: 8
|                                |||
||                               ||||||
||||                             || n
|||||||| *                       |||| nn
|||||| n                         |||||||| nnnn
|| nnn *                         |||||| nnnnnnnnn
|||| nnnnnn *                    || nnnnnnnnn 9
|||||||| nn 9 *                  |||| nnnnnnnn 999
|||||| nnnnn 99 *                |||||||| nnnnnn 9999999
|| n 99999 *                     |||||| nnn 99999 8
The solution is: 888
```

### Input-Output Example

#### Sample Input #1

```
||
||
|||
||||
nnnnnn 9
||| n
n
9
|||
8
```

#### Sample Output #1

```
|                                 || 
|| *                              |||| 
The solution is: |||| 
|                                 ||| 
||                                |||||| 
|||| *                            || n 
The solution is: || n 
| *                               nnnnnn 9 
||                                nn 999 
|||| *                            nnnn 999999 
|||||||| *                        nnnnnnnn 99 8 
The solution is: nnnnnnnn 88 
|                                 n 
||                                nn 
|||| *                            nnnn 
||||||||                          nnnnnnnn 
|||||| n                          nnnnnn 9 
|| nnn *                          nn 999 
|||| nnnnnn *                     nnnn 999999 
The solution is: 8 
|                                 ||| 
||                                |||||| 
||||                              || n 
|||||||| *                        |||| nn 
|||||| n                          |||||||| nnnn 
|| nnn *                          |||||| nnnnnnnnn 
|||| nnnnnn *                     || nnnnnnnnn 9 
|||||||| nn 9 *                   |||| nnnnnnnn 999 
|||||| nnnnn 99 *                 |||||||| nnnnnn 9999999 
|| n 99999 *                      |||||| nnn 99999 8 
The solution is: 888 
```
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
