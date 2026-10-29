# Second fresh set (for the fixed code, tag `extractor-v2`)

`extractor-v2` was fixed while looking at the first holdout (eval/HOLDOUT.md), so that set can no longer test it.
Record these 14 NEW sentences exactly as before, download as `holdout2-set.json`, run
`python eval/score.py eval/holdout2-set.json`, and put the score in the README whatever it is.
Do not change `extract.py` between recording and scoring.

| # | Say | Amount | Day |
|---|---|---|---|
| 1 | Naan Tuesday-ku two thousand rupees tharen | 2000 | Tuesday |
| 2 | Next Friday-ku ten thousand rupees pay pannuren | 10000 | next Friday |
| 3 | Naan naalaikku four thousand five hundred rupees kattuven | 4500 | tomorrow |
| 4 | Day after tomorrow-ku seven thousand rupees anupuren | 7000 | day after tomorrow |
| 5 | Naan tenth-ku fifteen thousand rupees tharen | 15000 | 10th |
| 6 | Naan Sunday-ku sixty thousand rupees kattuven | 60000 | Sunday |
| 7 | Naan fifteenth-ku twelve thousand rupees pay pannuren | 12000 | 15th |
| 8 | Naan month end-la fifty thousand rupees tharen | 50000 | end of month |
| 9 | Naan Wednesday-ku three lakh rupees pay pannuren | 300000 | Wednesday |
| 10 | Naan innaikku six hundred rupees tharen | 600 | today |
| 11 | Naan Monday-ku one thousand five hundred rupees kattuven | 1500 | Monday |
| 12 | Naan Saturday-ku eighty thousand rupees tharen | 80000 | Saturday |
| 13 | Naan Thursday-ku five thousand rupees pay pannuren (TV or fan on) | 5000 | Thursday |
| 14 | (Language: English India) I will pay two thousand rupees on Monday | 2000 | Monday |

Sentence 12 (eighty) and any ninety are included on purpose: those spellings in the lexicon are guesses, not seen yet.
