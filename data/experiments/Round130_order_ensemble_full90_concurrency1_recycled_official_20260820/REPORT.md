# RWKV-E2E-90

This suite gives RWKV only a user goal, an isolated workspace, generic constraints, and the Harness contract. Task Graphs, actions, repair paths, and external acceptance are not provided to the model.

- Cases run: 90
- Case concurrency: 1
- Agent completed: 64
- External acceptance passed: 34
- Strict E2E passed: 33

| Task | Group | Native level | Agent | External | Strict | Model requests | Actions | Protocol rejects |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: |
| E2E-B01 | basic | basic | PASS | PASS | PASS | 5 | 2 | 0 |
| E2E-B02 | basic | basic | PASS | PASS | PASS | 11 | 4 | 0 |
| E2E-B03 | basic | basic | PASS | PASS | PASS | 87 | 32 | 0 |
| E2E-B04 | basic | basic | FAIL | FAIL | FAIL | 562 | 189 | 11 |
| E2E-B05 | basic | basic | PASS | FAIL | FAIL | 5 | 2 | 0 |
| E2E-B06 | basic | basic | PASS | PASS | PASS | 14 | 4 | 1 |
| E2E-B07 | basic | basic | PASS | PASS | PASS | 14 | 3 | 2 |
| E2E-B08 | basic | basic | PASS | PASS | PASS | 14 | 4 | 1 |
| E2E-B09 | basic | basic | PASS | PASS | PASS | 8 | 3 | 0 |
| E2E-B10 | basic | basic | PASS | PASS | PASS | 14 | 5 | 0 |
| E2E-M01 | medium | medium | FAIL | FAIL | FAIL | 62 | 9 | 12 |
| E2E-M02 | medium | medium | PASS | PASS | PASS | 14 | 5 | 0 |
| E2E-M03 | medium | medium | PASS | PASS | PASS | 5 | 2 | 0 |
| E2E-M04 | medium | medium | PASS | FAIL | FAIL | 32 | 11 | 0 |
| E2E-M05 | medium | medium | PASS | PASS | PASS | 17 | 5 | 1 |
| E2E-M06 | medium | medium | PASS | FAIL | FAIL | 26 | 9 | 0 |
| E2E-M07 | medium | medium | PASS | PASS | PASS | 11 | 4 | 0 |
| E2E-M08 | medium | medium | PASS | FAIL | FAIL | 8 | 3 | 0 |
| E2E-M09 | medium | medium | FAIL | FAIL | FAIL | 547 | 195 | 5 |
| E2E-M10 | medium | medium | PASS | FAIL | FAIL | 20 | 7 | 0 |
| E2E-H01 | hard | hard | FAIL | FAIL | FAIL | 90 | 31 | 1 |
| E2E-H02 | hard | hard | FAIL | FAIL | FAIL | 348 | 191 | 9 |
| E2E-H03 | hard | hard | PASS | FAIL | FAIL | 8 | 1 | 2 |
| E2E-H04 | hard | hard | PASS | PASS | PASS | 2 | 1 | 0 |
| E2E-H05 | hard | hard | FAIL | FAIL | FAIL | 231 | 192 | 8 |
| E2E-H06 | hard | hard | PASS | FAIL | FAIL | 41 | 12 | 2 |
| E2E-H07 | hard | hard | FAIL | FAIL | FAIL | 23 | 8 | 0 |
| E2E-H08 | hard | hard | PASS | FAIL | FAIL | 11 | 3 | 1 |
| E2E-H09 | hard | hard | PASS | FAIL | FAIL | 14 | 4 | 1 |
| E2E-H10 | hard | hard | PASS | PASS | PASS | 23 | 8 | 0 |
| E2E-LH01 | hard | long_horizon | FAIL | FAIL | FAIL | 475 | 199 | 1 |
| E2E-LH02 | hard | long_horizon | FAIL | FAIL | FAIL | 515 | 189 | 11 |
| E2E-LH03 | hard | long_horizon | FAIL | FAIL | FAIL | 547 | 191 | 9 |
| E2E-LH04 | hard | long_horizon | PASS | FAIL | FAIL | 192 | 77 | 2 |
| E2E-LH05 | hard | long_horizon | FAIL | FAIL | FAIL | 354 | 129 | 12 |
| E2E-LH06 | hard | long_horizon | PASS | FAIL | FAIL | 41 | 12 | 2 |
| E2E-LH07 | hard | long_horizon | FAIL | FAIL | FAIL | 483 | 189 | 11 |
| E2E-LH08 | hard | long_horizon | FAIL | FAIL | FAIL | 59 | 8 | 12 |
| E2E-LH09 | hard | long_horizon | PASS | FAIL | FAIL | 26 | 6 | 3 |
| E2E-LH10 | hard | long_horizon | FAIL | FAIL | FAIL | 550 | 190 | 10 |
| E2E-LH11 | hard | long_horizon | FAIL | FAIL | FAIL | 209 | 175 | 12 |
| E2E-LH12 | hard | long_horizon | FAIL | FAIL | FAIL | 483 | 191 | 9 |
| E2E-B11 | basic | basic | PASS | PASS | PASS | 8 | 3 | 0 |
| E2E-B12 | basic | basic | PASS | PASS | PASS | 8 | 3 | 0 |
| E2E-B13 | basic | basic | PASS | PASS | PASS | 5 | 2 | 0 |
| E2E-B14 | basic | basic | PASS | FAIL | FAIL | 11 | 4 | 0 |
| E2E-B15 | basic | basic | PASS | PASS | PASS | 8 | 3 | 0 |
| E2E-B16 | basic | basic | FAIL | FAIL | FAIL | 502 | 199 | 1 |
| E2E-B17 | basic | basic | PASS | PASS | PASS | 427 | 155 | 1 |
| E2E-B18 | basic | basic | PASS | FAIL | FAIL | 67 | 22 | 2 |
| E2E-B19 | basic | basic | PASS | FAIL | FAIL | 14 | 3 | 2 |
| E2E-B20 | basic | basic | PASS | PASS | PASS | 14 | 5 | 0 |
| E2E-B21 | basic | basic | PASS | PASS | PASS | 11 | 3 | 1 |
| E2E-B22 | basic | basic | PASS | FAIL | FAIL | 8 | 3 | 0 |
| E2E-B23 | basic | basic | PASS | PASS | PASS | 11 | 4 | 0 |
| E2E-B24 | basic | basic | PASS | FAIL | FAIL | 8 | 3 | 0 |
| E2E-B25 | basic | basic | PASS | PASS | PASS | 11 | 4 | 0 |
| E2E-B26 | basic | basic | FAIL | PASS | FAIL | 559 | 200 | 0 |
| E2E-B27 | basic | basic | PASS | PASS | PASS | 8 | 3 | 0 |
| E2E-B28 | basic | basic | PASS | PASS | PASS | 5 | 2 | 0 |
| E2E-B29 | basic | basic | PASS | PASS | PASS | 11 | 4 | 0 |
| E2E-B30 | basic | basic | PASS | PASS | PASS | 14 | 5 | 0 |
| E2E-M11 | medium | medium | FAIL | FAIL | FAIL | 59 | 19 | 1 |
| E2E-M12 | medium | medium | PASS | PASS | PASS | 17 | 5 | 1 |
| E2E-M13 | medium | medium | PASS | FAIL | FAIL | 8 | 3 | 0 |
| E2E-M14 | medium | medium | PASS | FAIL | FAIL | 20 | 7 | 0 |
| E2E-M15 | medium | medium | PASS | FAIL | FAIL | 17 | 5 | 1 |
| E2E-M16 | medium | medium | PASS | FAIL | FAIL | 73 | 25 | 1 |
| E2E-M17 | medium | medium | PASS | FAIL | FAIL | 29 | 9 | 1 |
| E2E-M18 | medium | medium | PASS | FAIL | FAIL | 14 | 5 | 0 |
| E2E-M19 | medium | medium | PASS | FAIL | FAIL | 11 | 4 | 0 |
| E2E-M20 | medium | medium | PASS | PASS | PASS | 17 | 5 | 1 |
| E2E-M21 | medium | medium | PASS | PASS | PASS | 14 | 4 | 1 |
| E2E-M22 | medium | medium | PASS | FAIL | FAIL | 14 | 5 | 0 |
| E2E-M23 | medium | medium | PASS | FAIL | FAIL | 8 | 3 | 0 |
| E2E-M24 | medium | medium | PASS | PASS | PASS | 14 | 5 | 0 |
| E2E-M25 | medium | medium | PASS | FAIL | FAIL | 58 | 19 | 2 |
| E2E-M26 | medium | medium | PASS | PASS | PASS | 11 | 4 | 0 |
| E2E-M27 | medium | medium | PASS | FAIL | FAIL | 11 | 3 | 1 |
| E2E-M28 | medium | medium | PASS | FAIL | FAIL | 47 | 15 | 1 |
| E2E-M29 | medium | medium | PASS | FAIL | FAIL | 11 | 4 | 0 |
| E2E-M30 | medium | medium | PASS | PASS | PASS | 20 | 7 | 0 |
| E2E-H11 | hard | hard | FAIL | FAIL | FAIL | 482 | 198 | 2 |
| E2E-H12 | hard | hard | FAIL | FAIL | FAIL | 133 | 50 | 7 |
| E2E-H13 | hard | hard | FAIL | FAIL | FAIL | 100 | 38 | 12 |
| E2E-H14 | hard | hard | FAIL | FAIL | FAIL | 535 | 190 | 10 |
| E2E-H15 | hard | hard | FAIL | FAIL | FAIL | 494 | 196 | 4 |
| E2E-H16 | hard | hard | FAIL | FAIL | FAIL | 56 | 7 | 12 |
| E2E-H17 | hard | hard | PASS | FAIL | FAIL | 5 | 1 | 0 |
| E2E-H18 | hard | hard | FAIL | FAIL | FAIL | 50 | 16 | 0 |
