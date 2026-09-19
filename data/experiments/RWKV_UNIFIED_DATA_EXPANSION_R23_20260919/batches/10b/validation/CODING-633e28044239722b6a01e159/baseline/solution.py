#!/usr/bin/env python3

import sys

def read_point(line):
    return tuple(map(float, line.strip().split()))

def read_polyline(n):
    points = []
    for _ in range(n + 1):
        points.append(read_point(sys.stdin.readline()))
    return points

def distance_sq(p, q):
    return (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2

def closest_point_on_segment(p, a, b):
    ax, ay = a
    bx, by = b
    px, py = p

    abx = bx - ax
    aby = by - ay
    apx = px - ax
    apy = py - ay

    ab_len_sq = abx * abx + aby * aby
    if ab_len_sq == 0:
        return a

    t = (apx * abx + apy * aby) / ab_len_sq
    t = max(0.0, min(1.0, t))

    cx = ax + t * abx
    cy = ay + t * aby
    return (cx, cy)

def solve():
    M = read_point(sys.stdin.readline())
    n = int(sys.stdin.readline())
    polyline = read_polyline(n)

    best_dist_sq = float('inf')
    best_point = None

    for i in range(n):
        a = polyline[i]
        b = polyline[i + 1]
        p = closest_point_on_segment(M, a, b)
        d_sq = distance_sq(p, M)
        if d_sq < best_dist_sq:
            best_dist_sq = d_sq
            best_point = p

    print("{:.4f}".format(best_point[0]))
    print("{:.4f}".format(best_point[1]))

if __name__ == "__main__":
    solve()
