"""Independent validator reference: optimal depth-parity play, not Agent data."""
import sys


def solve(n):
    depth = n.bit_length() - 1
    value, player = 1, 0
    while value <= n:
        value = 2 * value + int((player == 0) == (depth % 2 == 0))
        player ^= 1
    return 'Takahashi' if player == 0 else 'Aoki'


if __name__ == '__main__':
    print(solve(int(sys.stdin.buffer.read())))
