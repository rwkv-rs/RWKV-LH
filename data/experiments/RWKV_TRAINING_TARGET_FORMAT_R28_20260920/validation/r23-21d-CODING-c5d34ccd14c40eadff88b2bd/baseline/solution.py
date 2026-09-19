{
  "implementation": "def fibonacci_schemes(n):\n    if n <= 2:\n        return 1\n    a, b = 1, 1\n    count = 0\n    while b <= n:\n        count += 1\n        a, b = b, a + b\n    return count\n\nif __name__ == \"__main__\":\n    import sys\n    n = int(sys.stdin.readline().strip())\n    print(fibonacci_schemes(n))",
  "notes": "The Fibonacci sequence is defined as F1 = 1, F2 = 1, and Fn = Fn-1 + Fn-2 for n >= 3. The number of distinct Fibonacci numbers up to n is the number of terms in the sequence that are <= n. This is computed by iterating through the sequence until the next term exceeds n. The implementation uses a simple iterative approach to count the terms."
}
