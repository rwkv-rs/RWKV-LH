At the recently concluded ICPC Hangzhou site, Team E experienced the thrilling process of rolling the leaderboard. She found that the most enjoyable part of ACM is rolling the leaderboard and reading team names.

## Problem Description

An ICPC official competition lasts for 5 hours.

The ranking of teams is determined by the number of problems solved and the penalty time. Teams with more problems solved rank higher. If the number of problems solved is the same, teams with less penalty time rank higher. Teams with both the same number of problems solved and the same penalty time have the same rank. In this problem, it is possible for teams to have the same rank, in which case, the team that appears first in the submission records is considered to rank higher.

Penalty time is determined by the time when problems are solved and the number of unsuccessful submissions before solving each problem. The penalty time is the sum of the minutes from the start of the competition when each problem is solved, plus 20 minutes times the number of unsuccessful submissions before solving that problem. For example, if a team solved problem G at 1:28:35 into the competition and had 3 unsuccessful submissions before that, the total contribution to the penalty time for problem G would be $88 + 3 \times 20 = 148$ minutes.

**It is important to note that only unsuccessful submissions for problems that are eventually solved are counted towards the penalty time.** For example, if a team had 14 unsuccessful submissions for problem I but never solved it by the end of the competition, those 14 unsuccessful submissions would not be counted towards the penalty time. **After a problem is solved, any subsequent submissions (whether successful or not) by the team for that problem will not affect the result or the penalty time for that problem.**

During the competition, contestants can submit code for any problem at any time, and the code will be immediately judged and the result returned (e.g., $\texttt{Accepted}$, $\texttt{Time Limit Exceeded}$, $\texttt{Memory Limit Exceeded}$, $\texttt{Presentation Error}$, $\texttt{Wrong Answer}$, $\texttt{Runtime Error}$). Among these, $\texttt{Accepted}$ indicates a successful submission, while all other results indicate unsuccessful submissions.

During the first four hours of the competition ($0:00:00 \sim 4:00:00$), all submissions by each team are reflected on the leaderboard. During the last hour of the competition ($4:00:01 \sim 5:00:00$), the leaderboard is frozen, and all submissions on the leaderboard for each team and each problem are shown as pending judgment (the submitting team knows the result).

After the competition, there is a tense and exciting process of rolling the leaderboard. The guest rolling the leaderboard will follow the frozen leaderboard, starting from the last place and moving up to the first place, **first reading out the team name**, and then, in order from problem A to the last problem, announcing whether the "pending judgment" status problems for that team were eventually solved.

If a problem was solved, the rankings of all teams will be immediately recalculated. Obviously, the rankings of teams that have already been rolled (had their team names read out and all pending judgment status results revealed) will not be affected. If the team's rank improves, the guest rolling the leaderboard will immediately start rolling the next team. Therefore, a team's name may be read out multiple times by the guest rolling the leaderboard.

For example, a team named "TunTi" did not solve any problems in the first four hours and was ranked last at the time of the leaderboard freeze. After the freeze, the team solved all thirteen problems consecutively. Thus, the guest rolling the leaderboard might read out the team's name seven or eight times. Of course, once the team rises to the first place, its rank will not change again, even if the revealed judgment results indicate a successful submission, but since its rank did not change, the guest will not read out its name again.

Given the complete submission records of an ICPC competition, please output the team names read out by the guest rolling the leaderboard in order.

**Teams with no submission records will not appear on the leaderboard or be read out during the rolling of the leaderboard.**

## Input Format

The first line of input contains three integers $n, m, K$, representing the number of problems, the number of teams, and the number of submission records in the ICPC competition, respectively.

The next $K$ lines each contain four space-separated strings, representing a submission record. The first string, in the form $x:yy:zz$, indicates the time of submission as $x$ hours, $yy$ minutes, and $zz$ seconds after the start of the competition. The second string is a capital English letter representing the problem's identifier (e.g., $\texttt{A, B, ...}$). The third string is the team name, which is guaranteed not to contain spaces. The fourth string (which may contain spaces but will only be one of the six judgment results mentioned in the problem description) is the judgment result of the submission, with the specific meanings of the strings as described in the problem description section.

## Output Format

Output several lines, representing the team names read out by the guest rolling the leaderboard in order.

## Sample Input and Output

### Sample Input #1

```
2 2 4
0:00:01 A abc Wrong Answer
0:00:02 A abc Accepted
0:19:38 A bcd Accepted
4:18:22 B abc Accepted
```

### Sample Output #1

```
abc
bcd
abc
```

## Notes/Hints

### Sample Explanation

Before the leaderboard freeze, team $\texttt{abc}$ only solved problem $\texttt{A}$, and had one incorrect submission before the first correct submission at the second second, so the penalty time is 20 minutes; team $\texttt{bcd}$ also only solved problem $\texttt{A}$, and had no incorrect submissions before the first correct submission at 0:19:38, so the penalty time is 19 minutes.

After the leaderboard freeze, team $\texttt{abc}$ solved problem $\texttt{B}$.

At the start of the rolling leaderboard, since the submissions after the freeze have not been revealed, it is temporarily assumed that both teams $\texttt{abc}$ and $\texttt{bcd}$ only solved one problem, with the former having a higher penalty time and thus ranking lower.

Following the principle of starting from the last place and moving up, the name of team $\texttt{abc}$ is read out first, and the results of their submissions after the freeze are revealed. They solved problem $\texttt{B}$, so their number of problems solved is updated to 2, and the penalty time is also updated. Meanwhile, the rankings of all teams are immediately recalculated. Since at this point $\texttt{abc}$ has more problems solved than $\texttt{bcd}$, their rank is recalculated to first place, while $\texttt{bcd}$ becomes the last place.

After that, the name of team $\texttt{bcd}$ is read out, as they had no submissions after the freeze, so the rankings of all teams do not change, and the guest will proceed to roll the leaderboard for the next team.

Finally, the name of team $\texttt{abc}$ is read out, and the rolling of the leaderboard ends.

It should be noted that during the rolling of the leaderboard, submissions are revealed problem by problem. That is, if a team solved multiple problems after the freeze, during their rolling process, as soon as the first "pending judgment" status problem is revealed to be solved, the subsequent "pending judgment" status problems are temporarily not revealed, but instead, the ranking update process and the possible change to rolling another team immediately take place.

### Data Size and Constraints

- For 30% of the data, $n = 1$;
- For another 10% of the data, $m = 1$;
- For 100% of the data, $1 \le n \le 20$, $1 \le m \le 1000$, $1 \le K \le 10^4$, $0 \leq x \leq 5$, $00 \leq yy < 60$, $00 \leq zz < 60$, and when $x = 5$, it is guaranteed that $yy = zz = 00$.

The submission records are given in non-decreasing order of submission time, i.e., the submission time of earlier records will not be later than that of later records. The problem names are uppercase letters $\texttt{A} \sim \texttt{Z}$, the team names are strings of no more than 50 lowercase letters, and the judgment statuses are one of the six given in the problem description.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
