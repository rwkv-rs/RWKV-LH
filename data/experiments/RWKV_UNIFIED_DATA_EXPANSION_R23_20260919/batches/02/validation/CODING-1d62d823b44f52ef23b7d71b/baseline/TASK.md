Given a string of length 9 containing unknown characters represented by '*' (without quotes). Below, you are given n strings of length 9. If a string from the input matches the initial string except for the unknown parts, it is considered valid. Output the number of valid strings and each valid string.

For example, if the initial string is A58**52*1, then the string A58ZS52T1 is valid, while the string A589992G1 is not.

## Problem Description

The number of cars traveling to the city center daily in Default City far exceeds the number of available parking spots. The City Council introduced parking fees to address the issue of overspill parking on city streets. Parking fees are enforced using automated vehicle registration plate scanners that capture the vehicle's registration plate, recognize the sequence of digits and letters, and check it against a vehicle registration database to ensure fees are paid or to automatically issue fines otherwise.

Shortly after the introduction of parking fees, a fraud emerged. Some vehicle owners began to cover one or several digits or letters on their registration plates with paper while parked, making it impossible for the scanner to recognize the vehicle's registration code and issue a fine.

The Default City Council established the Fraud Busters Initiative (FBI) to design a solution to prevent this type of fraud. The FBI's approach is to expand the number of vehicle features recognized by scanners (including features like vehicle type and color) and exclude any vehicles detected elsewhere at the same time. This information should help identify the correct vehicle by narrowing down the search in the vehicle registration database.

You work for the FBI. Your colleagues have already written the complex recognition software that analyzes various vehicle features and provides you with a list of potential registration codes for a scanned car. Your task is to take this list and a partially recognized code from the license plate and find all matching registration codes.

## Input Format

The first line of the input file contains 9 characters of the code recognized by the scanner. The recognized code is represented as a sequence of 9 digits, uppercase English letters, and '*' characters. '*' represents a digit or letter that the scanner could not recognize.

The second line of the input file contains a single integer n (1 ≤ n ≤ 1000) — the number of vehicle registration codes from the vehicle registration database.

The following n lines contain the corresponding registration codes, one code per line. Vehicle registration codes are represented as a sequence of 9 digits and uppercase English letters. All codes on these n lines of the input file are different.

## Output Format

On the first line of the output file, write a single integer k (0 ≤ k ≤ n) — the number of codes from the input file that match the code recognized by the scanner. A code from the scanner matches a code from the database if the characters at all corresponding positions in the codes are equal or the character from the scanner code is '*'.

On the following k lines, write the matching codes, one code per line, in the same order as they are given in the input file.

## Sample Input and Output

### Input Sample #1

```
A**1MP19*
4
A001MP199
E885EE098
A111MP199
KT7351TTB
```

### Output Sample #1

```
2
A001MP199
A111MP199
```

## Notes

Time limit: 1 second, Memory limit: 128 MB.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
