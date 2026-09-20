On the Island of Logic, there are three types of inhabitants, and all the island's residents know each other:

- Divine beings: They always tell the truth.
- Evil spirits: They always lie.
- Humans: They tell the truth during the day and lie at night.

A social scientist has arrived on the island. He does not know who the residents are, so he needs you to create a lie detector to help him understand which statements are true, which are false, and what type the speaker is.

## **Input Format**

The input consists of multiple sets of data. Each set has the following format, and when the input is 0, the input ends.

Each data set starts with an integer `n`, followed by `n` lines, each in one of the following formats:

- `X: I am [not] (divine|evil|human|lying)`
  
  X says: I am (not) divine|evil|human|lying

- `X is [not] (divine|evil|human|lying)`
  
  X says: X is (not) divine|evil|human|lying

- `It is (day|night)`
  
  X says: It is day|night

Where X represents one of the five people: A, B, C, D, or E.

## **Output Format**

The output consists of multiple lines. The first line outputs `Conversation #` (indicating the current data set number), followed by each line of the conclusions derived, which can be one of the following:

- `This is impossible`

  This statement cannot occur.

- `No facts are deductible`

  Cannot determine.

- `X is divine|evil|human`

  X is divine|evil|human.

- `It is day|night`

  It is day|night.

## Input and Output Samples

### Sample Input #1

```
1
A: I am divine.
1
A: I am lying.
1
A: I am evil.
3
A: B is human.
B: A is evil.
A: B is evil.
0
```

### Sample Output #1

```
Conversation #1
No facts are deducible.
Conversation #2
This is impossible.
Conversation #3
A is human.
It is night.
Conversation #4
A is evil.
B is divine.
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
