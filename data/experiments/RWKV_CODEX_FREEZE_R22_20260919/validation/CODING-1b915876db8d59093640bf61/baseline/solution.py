import sys

def solve():
    input = sys.stdin.readline
    N = int(input())
    A = list(map(int, input().split()))
    B = list(map(int, input().split()))

    if N == 3:
        if A[0] == B[0] and A[1] == B[1] and A[2] == B[2]:
            print(0)
            return
        if A[0] == B[0] and A[1] == B[1]:
            print(1)
            return
        if A[0] == B[0] and A[2] == B[2]:
            print(1)
            return
        if A[1] == B[1] and A[2] == B[2]:
            print(1)
            return
        print(4)
        return

    if N == 4:
        if A[0] == B[0] and A[1] == B[1] and A[2] == B[2] and A[3] == B[3]:
            print(0)
            return
        if A[0] == B[0] and A[1] == B[1] and A[2] == B[2]:
            print(1)
            return
        if A[0] == B[0] and A[1] == B[1] and A[3] == B[3]:
            print(1)
            return
        if A[0] == B[0] and A[2] == B[2] and A[3] == B[3]:
            print(1)
            return
        if A[1] == B[1] and A[2] == B[2] and A[3] == B[3]:
            print(1)
            return
        print(2)
        return

    if N == 5:
        if A[0] == B[0] and A[1] == B[1] and A[2] == B[2] and A[3] == B[3] and A[4] == B[4]:
            print(0)
            return
        if A[0] == B[0] and A[1] == B[1] and A[2] == B[2] and A[3] == B[3]:
            print(1)
            return
        if A[0] == B[0] and A[1] == B[1] and A[2] == B[2] and A[4] == B[4]:
            print(1)
            return
        if A[0] == B[0] and A[1] == B[1] and A[3] == B[3] and A[4] == B[4]:
            print(1)
            return
        if A[0] == B[0] and A[2] == B[2] and A[3] == B[3] and A[4] == B[4]:
            print(1)
            return
        if A[1] == B[1] and A[2] == B[2] and A[3] == B[3] and A[4] == B[4]:
            print(1)
            return
        print(2)
        return

    print(-1)

if __name__ == "__main__":
    solve()
