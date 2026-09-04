# Round159 Supervisor Relay Stability

| model | raw success | schema | exact | 5xx | p50 ms | p95 ms | tokens | candidate |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|
| gpt-5.4 | 5/5 | 5/5 | 5/5 | 0 | 2312.6 | 7020.4 | 37634 | True |
| gpt-5.4-2026-03-05 | 0/5 | 0/5 | 0/5 | 5 | 267.9 | 273.5 | 0 | False |
| gpt-5.5-2026-04-23 | 0/5 | 0/5 | 0/5 | 5 | 271.5 | 282.3 | 0 | False |
| gpt-5.6-terra | 5/5 | 5/5 | 5/5 | 0 | 2993.9 | 4661.4 | 2396 | True |
| gpt-5.6-sol | 5/5 | 5/5 | 5/5 | 0 | 3090.5 | 5718.0 | 2388 | True |
| claude-sonnet-4-6 | 5/5 | 0/5 | 0/5 | 0 | 4104.8 | 4185.2 | 0 | False |
