# RWKV-E2E-90

RWKV receives only the user goal, isolated workspace, generic constraints, and the Harness contract. Task Graphs, actions, repair paths, and external acceptance are not provided to the model.

- Cases run: 90
- Case concurrency: 8
- Agent completed: 0
- External acceptance passed: 3
- Strict E2E passed: 0
- Supervisor requests: 0

| Task | Group | Native level | Agent | External | Strict | RWKV requests | Supervisor requests | Actions | Protocol rejects |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B01 | basic | basic | FAIL | PASS | FAIL | 57 | 0 | 22 | 12 |
| E2E-B02 | basic | basic | FAIL | FAIL | FAIL | 9 | 0 | 3 | 2 |
| E2E-B03 | basic | basic | FAIL | FAIL | FAIL | 9 | 0 | 3 | 2 |
| E2E-B04 | basic | basic | FAIL | FAIL | FAIL | 9 | 0 | 3 | 2 |
| E2E-B05 | basic | basic | FAIL | PASS | FAIL | 57 | 0 | 22 | 12 |
| E2E-B06 | basic | basic | FAIL | FAIL | FAIL | 9 | 0 | 3 | 2 |
| E2E-B07 | basic | basic | FAIL | FAIL | FAIL | 9 | 0 | 3 | 2 |
| E2E-B08 | basic | basic | FAIL | FAIL | FAIL | 9 | 0 | 3 | 2 |
| E2E-B09 | basic | basic | FAIL | FAIL | FAIL | 9 | 0 | 3 | 2 |
| E2E-B10 | basic | basic | FAIL | FAIL | FAIL | 15 | 0 | 1 | 12 |
| E2E-M01 | medium | medium | FAIL | FAIL | FAIL | 13 | 0 | 0 | 12 |
| E2E-M02 | medium | medium | FAIL | FAIL | FAIL | 9 | 0 | 3 | 2 |
| E2E-M03 | medium | medium | FAIL | FAIL | FAIL | 17 | 0 | 2 | 12 |
| E2E-M04 | medium | medium | FAIL | FAIL | FAIL | 15 | 0 | 1 | 12 |
| E2E-M05 | medium | medium | FAIL | FAIL | FAIL | 17 | 0 | 2 | 12 |
| E2E-M06 | medium | medium | FAIL | FAIL | FAIL | 9 | 0 | 3 | 2 |
| E2E-M07 | medium | medium | FAIL | FAIL | FAIL | 9 | 0 | 3 | 2 |
| E2E-M08 | medium | medium | FAIL | FAIL | FAIL | 15 | 0 | 1 | 12 |
| E2E-M09 | medium | medium | FAIL | FAIL | FAIL | 17 | 0 | 2 | 12 |
| E2E-M10 | medium | medium | FAIL | FAIL | FAIL | 57 | 0 | 22 | 12 |
| E2E-H01 | hard | hard | FAIL | FAIL | FAIL | 13 | 0 | 0 | 12 |
| E2E-H02 | hard | hard | FAIL | FAIL | FAIL | 13 | 0 | 0 | 12 |
| E2E-H03 | hard | hard | FAIL | FAIL | FAIL | 10 | 0 | 3 | 2 |
| E2E-H04 | hard | hard | FAIL | PASS | FAIL | 57 | 0 | 22 | 12 |
| E2E-H05 | hard | hard | FAIL | FAIL | FAIL | 15 | 0 | 1 | 12 |
| E2E-H06 | hard | hard | FAIL | FAIL | FAIL | 13 | 0 | 0 | 12 |
| E2E-H07 | hard | hard | FAIL | FAIL | FAIL | 15 | 0 | 1 | 12 |
| E2E-H08 | hard | hard | FAIL | FAIL | FAIL | 9 | 0 | 3 | 2 |
| E2E-H09 | hard | hard | FAIL | FAIL | FAIL | 17 | 0 | 2 | 12 |
| E2E-H10 | hard | hard | FAIL | FAIL | FAIL | 13 | 0 | 0 | 12 |
| E2E-LH01 | hard | long_horizon | FAIL | FAIL | FAIL | 13 | 0 | 0 | 12 |
| E2E-LH02 | hard | long_horizon | FAIL | FAIL | FAIL | 17 | 0 | 2 | 12 |
| E2E-LH03 | hard | long_horizon | FAIL | FAIL | FAIL | 13 | 0 | 0 | 12 |
| E2E-LH04 | hard | long_horizon | FAIL | FAIL | FAIL | 13 | 0 | 0 | 12 |
| E2E-LH05 | hard | long_horizon | FAIL | FAIL | FAIL | 13 | 0 | 0 | 12 |
| E2E-LH06 | hard | long_horizon | FAIL | FAIL | FAIL | 13 | 0 | 0 | 12 |
| E2E-LH07 | hard | long_horizon | FAIL | FAIL | FAIL | 13 | 0 | 0 | 12 |
| E2E-LH08 | hard | long_horizon | FAIL | FAIL | FAIL | 9 | 0 | 3 | 2 |
| E2E-LH09 | hard | long_horizon | FAIL | FAIL | FAIL | 59 | 0 | 23 | 12 |
| E2E-LH10 | hard | long_horizon | FAIL | FAIL | FAIL | 17 | 0 | 2 | 12 |
| E2E-LH11 | hard | long_horizon | FAIL | FAIL | FAIL | 13 | 0 | 0 | 12 |
| E2E-LH12 | hard | long_horizon | FAIL | FAIL | FAIL | 17 | 0 | 2 | 12 |
| E2E-B11 | basic | basic | FAIL | FAIL | FAIL | 9 | 0 | 3 | 2 |
| E2E-B12 | basic | basic | FAIL | FAIL | FAIL | 9 | 0 | 3 | 2 |
| E2E-B13 | basic | basic | FAIL | FAIL | FAIL | 9 | 0 | 3 | 2 |
| E2E-B14 | basic | basic | FAIL | FAIL | FAIL | 9 | 0 | 3 | 2 |
| E2E-B15 | basic | basic | FAIL | FAIL | FAIL | 9 | 0 | 3 | 2 |
| E2E-B16 | basic | basic | FAIL | FAIL | FAIL | 15 | 0 | 1 | 12 |
| E2E-B17 | basic | basic | FAIL | FAIL | FAIL | 9 | 0 | 3 | 2 |
| E2E-B18 | basic | basic | FAIL | FAIL | FAIL | 9 | 0 | 3 | 2 |
| E2E-B19 | basic | basic | FAIL | FAIL | FAIL | 9 | 0 | 3 | 2 |
| E2E-B20 | basic | basic | FAIL | FAIL | FAIL | 9 | 0 | 3 | 2 |
| E2E-B21 | basic | basic | FAIL | FAIL | FAIL | 9 | 0 | 3 | 2 |
| E2E-B22 | basic | basic | FAIL | FAIL | FAIL | 9 | 0 | 3 | 2 |
| E2E-B23 | basic | basic | FAIL | FAIL | FAIL | 13 | 0 | 0 | 12 |
| E2E-B24 | basic | basic | FAIL | FAIL | FAIL | 9 | 0 | 3 | 2 |
| E2E-B25 | basic | basic | FAIL | FAIL | FAIL | 9 | 0 | 3 | 2 |
| E2E-B26 | basic | basic | FAIL | FAIL | FAIL | 9 | 0 | 3 | 2 |
| E2E-B27 | basic | basic | FAIL | FAIL | FAIL | 9 | 0 | 3 | 2 |
| E2E-B28 | basic | basic | FAIL | FAIL | FAIL | 9 | 0 | 3 | 2 |
| E2E-B29 | basic | basic | FAIL | FAIL | FAIL | 9 | 0 | 3 | 2 |
| E2E-B30 | basic | basic | FAIL | FAIL | FAIL | 9 | 0 | 3 | 2 |
| E2E-M11 | medium | medium | FAIL | FAIL | FAIL | 13 | 0 | 0 | 12 |
| E2E-M12 | medium | medium | FAIL | FAIL | FAIL | 13 | 0 | 0 | 12 |
| E2E-M13 | medium | medium | FAIL | FAIL | FAIL | 15 | 0 | 1 | 12 |
| E2E-M14 | medium | medium | FAIL | FAIL | FAIL | 13 | 0 | 0 | 12 |
| E2E-M15 | medium | medium | FAIL | FAIL | FAIL | 9 | 0 | 3 | 2 |
| E2E-M16 | medium | medium | FAIL | FAIL | FAIL | 13 | 0 | 0 | 12 |
| E2E-M17 | medium | medium | FAIL | FAIL | FAIL | 9 | 0 | 3 | 2 |
| E2E-M18 | medium | medium | FAIL | FAIL | FAIL | 9 | 0 | 3 | 2 |
| E2E-M19 | medium | medium | FAIL | FAIL | FAIL | 17 | 0 | 2 | 12 |
| E2E-M20 | medium | medium | FAIL | FAIL | FAIL | 13 | 0 | 0 | 12 |
| E2E-M21 | medium | medium | FAIL | FAIL | FAIL | 9 | 0 | 3 | 2 |
| E2E-M22 | medium | medium | FAIL | FAIL | FAIL | 9 | 0 | 3 | 2 |
| E2E-M23 | medium | medium | FAIL | FAIL | FAIL | 9 | 0 | 3 | 2 |
| E2E-M24 | medium | medium | FAIL | FAIL | FAIL | 13 | 0 | 0 | 12 |
| E2E-M25 | medium | medium | FAIL | FAIL | FAIL | 9 | 0 | 3 | 2 |
| E2E-M26 | medium | medium | FAIL | FAIL | FAIL | 15 | 0 | 1 | 12 |
| E2E-M27 | medium | medium | FAIL | FAIL | FAIL | 9 | 0 | 3 | 2 |
| E2E-M28 | medium | medium | FAIL | FAIL | FAIL | 13 | 0 | 0 | 12 |
| E2E-M29 | medium | medium | FAIL | FAIL | FAIL | 9 | 0 | 3 | 2 |
| E2E-M30 | medium | medium | FAIL | FAIL | FAIL | 13 | 0 | 0 | 12 |
| E2E-H11 | hard | hard | FAIL | FAIL | FAIL | 13 | 0 | 0 | 12 |
| E2E-H12 | hard | hard | FAIL | FAIL | FAIL | 13 | 0 | 0 | 12 |
| E2E-H13 | hard | hard | FAIL | FAIL | FAIL | 13 | 0 | 0 | 12 |
| E2E-H14 | hard | hard | FAIL | FAIL | FAIL | 13 | 0 | 0 | 12 |
| E2E-H15 | hard | hard | FAIL | FAIL | FAIL | 9 | 0 | 3 | 2 |
| E2E-H16 | hard | hard | FAIL | FAIL | FAIL | 17 | 0 | 2 | 12 |
| E2E-H17 | hard | hard | FAIL | FAIL | FAIL | 11 | 0 | 3 | 3 |
| E2E-H18 | hard | hard | FAIL | FAIL | FAIL | 13 | 0 | 0 | 12 |
