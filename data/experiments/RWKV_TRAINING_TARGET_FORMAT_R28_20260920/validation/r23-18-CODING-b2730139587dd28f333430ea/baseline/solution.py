import sys

def solve():
    data = sys.stdin.read().strip().split()
    if not data:
        return
    it = iter(data)
    N = int(next(it))
    P = [int(next(it)) - 1 for _ in range(N)]
    Q = [int(next(it)) - 1 for _ in range(N)]

    # Build inverse of Q: invQ[x] = index i such that Q[i] == x
    invQ = [0] * N
    for i in range(N):
        invQ[Q[i]] = i

    # Build permutation R where R[i] = invQ[P[i]]
    R = [invQ[x] for x in P]

    # Find cycles in R
    visited = [False] * N
    max_len = 0
    for i in range(N):
        if not visited[i]:
            cur = i
            length = 0
            while not visited[cur]:
                visited[cur] = True
                cur = R[cur]
                length += 1
            if length > max_len:
                max_len = length

    print(max_len)

if __name__ == "__main__":
    solve()
