RAID technology uses multiple disks to store data. Each piece of data is stored on more than one disk, allowing data recovery from other disks when one fails. This problem discusses one type of RAID technology. Data is divided into blocks of size `s` (1≤s≤64) bits and stored across `d` (2≤d≤6) disks. As shown in the diagram, for every `d-1` data blocks, there is a parity block, such that the XOR result of every `d` data blocks is all 0s (even parity) or all 1s (odd parity).

------------

For example, given `d=5`, `s=2`, even parity, the data `6C7A79EDFC` (in binary: 01101100 01111010 01111001 11101101 11111100) is stored as shown in the diagram.

------------

The blocks in bold are the parity blocks. You are given `d`, `s`, `b`, the type of parity (`E` for even parity, `O` for odd parity), and `b` (1≤b≤100) data blocks (where "?" indicates corrupted data). Your task is to recover and output the complete data. If the parity is incorrect or if there is too much corrupted data to recover, you should report that the disk is invalid.

## Input and Output Examples

### Input Example #1

```
5 2 5
E
0001011111
0110111011
1011011111
1110101100
0010010111
3 2 5
E
0001111111
0111111011
xx11011111
3 5 1
O
11111
11xxx
x1111
0
```

### Output Example #1

```
Disk set 1 is valid, contents are: 6C7A79EDFC
Disk set 2 is invalid.
Disk set 3 is valid, contents are: FFC
```
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
