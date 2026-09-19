> Remember that afternoon when a gentle rain began to fall outside the window.  
> I, who was taking the preliminary exam, heard the children playing on the street, heard the cars speeding by.  
> I think I heard the sound of rain.

---

This is a **written** question. You need to complete the following questions and submit your answers.

Your program needs to read an integer $T(1 \le T \le 5)$ representing the question number and output the corresponding answer.

## Problem Description

### Question 1

The sum of the binary numbers $00101100$ and $00010101$ is

A. $00101000$  
B. $01000001$  
C. $01000100$  
D. $00111000$ 

### Question 2

Which of the following sets of strings can be used as variable names in C++?

A. `print`  `_3d`  `db8`  `aBc`  
B. `I\am`  `one_half`  `start$it`  `3pai`  
C. `atr_1`  `Cpp`  `pow`  `while`  
D. `Pxq`  `My->book`  `line#`  `His.age`

### Question 3

There are $7$ identical seas, to be placed into $3$ identical packages (empty packages are allowed). There are ______ ways to do this.

### Question 4

On the weekend, Nanami and Mukuro, along with Himiko Toga, decided to cook three dishes together. Nanami is in charge of washing the vegetables, Mukuro is in charge of cutting them, and Himiko Toga is in charge of cooking. Assuming that each dish follows the sequence: washing for $10$ minutes, cutting for $10$ minutes, and cooking for $10$ minutes, each dish takes $30$ minutes. Note: The same step for different dishes cannot be done simultaneously. For example, the washing, cutting, or cooking of the first and second dishes cannot be done at the same time. What is the shortest time required to complete all three dishes?

### Question 5

Read the following C++ program and write down its output.

![](https://cdn.luogu.com.cn/upload/image_hosting/c8aevs2q.png)

## Input Format

Input an integer representing the question number.

## Output Format

Output your answer.

## Sample Input and Output

No test cases available.

## Notes

Answer template for reference.

```cpp
#include<iostream>
using namespace std;
int main() {
    string ans [] = {
        "The answer of problem 1", // Replace within the double quotes with the answer to Question 1
        "The answer of problem 2", // Replace within the double quotes with the answer to Question 2
        "The answer of problem 3", // Replace within the double quotes with the answer to Question 3
        "The answer of problem 4", // Replace within the double quotes with the answer to Question 4
        "The answer of problem 5", // Replace within the double quotes with the answer to Question 5
    };
    int T;
    cin >> T;
    cout << ans[T - 1] << endl;
    return 0;
}
```

Your output should strictly follow the above format.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
