You need to write a program to help your boss schedule meetings.

$I.$ Meeting Rules

For each input meeting, try to fit it into the schedule. If the requested time is not available, try to reschedule it to the same time on another day within the week. If this is still not possible, add the person to a list of unscheduled meetings. Otherwise, add the meeting to the schedule.

$II.$ Input Rules

For each meeting input, the first string is the name of the person being scheduled, and the second and third numbers represent the requested time.

**Each meeting must include a $10$ minute break afterward**. If conditions are not met, reschedule accordingly.

Appointments longer than $4$ hours or those that span the lunch period are automatically canceled.

Meetings initially planned for $5$ minutes should be rounded up to $10$ minutes.

$III.$ Output Rules

The first line should display: "APPOINTMENT SCHEDULE FOR THE WEEK"

The following lines should show the arranged meeting times.

The last few lines should list the names of individuals whose meetings could not be scheduled.

## Sample Input and Output

### Sample Input #1

```
Johnstone TUE 09 15 1 30
Peterson MON 09 00 0 30
McKeever FRI 09 30 1 00
Garzarelli THU 10 45 0 20
Tucker MON 10 00 2 30
Davis MON 02 30 1 00
Corrigan MON 02 00 0 15
Trump WED 01 00 3 00
Logan THU 09 45 1 05
Schulman THU 11 10 0 30
```

### Sample Output #1

```
APPOINTMENT SCHEDULE FOR THE WEEK
MONDAY
Peterson 9:00 to 9:30
Tucker 10:00 to 12:30
Davis 2:30 to 3:30
TUESDAY
Johnstone 9:10 to 10:50
Corrigan 2:00 to 2:20
WEDNESDAY
No Appointments Scheduled
THURSDAY
Garzarelli 10:40 to 11:10
FRIDAY
McKeever 9:30 to 10:30
Schulman 11:10 to 11:40
APPOINTMENTS COULD NOT BE SCHEDULED FOR:
Trump
Logan
```
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
