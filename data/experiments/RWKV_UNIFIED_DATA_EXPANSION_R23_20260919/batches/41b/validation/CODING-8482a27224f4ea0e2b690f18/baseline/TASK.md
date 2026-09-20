Software CRC

You work for a company that uses a large number of personal computers. Your boss, Dr. Penny Pincher, has wanted to connect the computers for some time but has been reluctant to spend money on the Ethernet boards you recommended. You inadvertently pointed out that each PC comes from the supplier with an asynchronous serial port, which requires no additional cost. Dr. Pincher, of course, sees her opportunity and assigns you the task of writing the necessary software for PC communication.

After reading some books on communications, you learn that every communication has errors, and a common solution to this problem is to attach some error-checking information to each message. This information allows the receiving program to detect when transmission errors occur (most of the time). So, you went to the library, borrowed the largest book on communications you could find, and spent your weekend (unpaid overtime) reading about error-checking.

In the end, you decide that CRC (Cyclic Redundancy Check) is the best error-checking solution for your situation and write a memo to Dr. Pincher detailing the proposed error-checking mechanism mentioned below.

CRC Generation

The message to be transmitted is treated as a long positive binary number. The first byte is treated as the most significant byte of the binary number. The second byte is the next most significant, and so on. This binary number will be called "M" (for message). Instead of transmitting "M", you will send a message "M2" composed of "M" followed by a two-byte CRC value. The CRC value is chosen so that when "M2" is divided by a certain 16-bit value "g", the remainder is zero. This allows the receiving program to easily determine if the message has been corrupted during transmission. It simply divides any received message by "g". If the remainder from the division is zero, it is assumed that no error occurred. You notice that most values recommended for "g" in the book are odd, but you don't understand any other similarities, so you choose the value 34943 for "g" (the generator value). You will design an algorithm for computing the CRC value corresponding to any message that may be sent. To test this algorithm, you will write a program that reads lines from standard input and writes to standard output.

Input:

Each line of input contains no more than 1024 characters (the maximum number of characters per line, excluding the line terminator character). The input is terminated by a line containing "#" in column 1.

Output:

For each input line, compute the CRC value of the message contained in the line and write the numerical value of the CRC bytes (in hexadecimal notation) onto an output line. Note that each printed CRC value should be between 0 and 34942 (in decimal).

Sample Input:

```
this is a test
A
#
```

Sample Output:

```
77 FD
00 00
0C 86
```

## Input and Output Samples

### Sample Input #1

```
this is a test
A
#
```

### Sample Output #1

```
77 FD
00 00
0C 86
```
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
