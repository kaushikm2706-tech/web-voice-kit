# Fresh clips the extractor has never seen (the real test)

The 23 development clips were used to write and tune `examples/voice-agent/extract.py`, so scores on them are
optimistic. This file is the plan for a fair test.

## Rules
1. Commit and tag the code first: `git tag extractor-v1`. After that, do not change `extract.py` until the score is recorded.
2. Record these in the demo page's **Eval set** panel, exactly like before: Language Tamil (English for the last one), wait for
   the pill to say **listening**, speak, wait 2 seconds, Stop, type Amount and Day, Add to eval set.
3. Download the file as `holdout-set.json` and run: `python eval/score.py holdout-set.json`.
4. Write the score into the README **whatever it is**, including the failures. Fix bugs only after that, as a new commit.

## Sentences (made up; reword naturally but keep the amount and day)
| # | Say | Amount | Day | Note |
|---|---|---|---|---|
| 1 | Naan Wednesday-ku fifteen hundred rupees pay pannuren | 1500 | Wednesday | |
| 2 | Next Monday-ku three thousand five hundred rupees tharen | 3500 | next Monday | |
| 3 | Naan naalaikku six thousand five hundred rupees kattuven | 6500 | tomorrow | |
| 4 | Naan day after tomorrow eight thousand rupees anupuren | 8000 | day after tomorrow | |
| 5 | Naan fifth-ku twenty thousand rupees pay pannuren | 20000 | 5th | |
| 6 | Naan Friday-ku forty thousand rupees tharen | 40000 | Friday | tests Friday vs forty |
| 7 | Naan twentieth-ku thirty thousand rupees kattuven | 30000 | 20th | |
| 8 | Naan month end-la seventy five thousand rupees tharen | 75000 | end of month | |
| 9 | Naan Saturday-ku two lakh rupees pay pannuren | 200000 | Saturday | |
| 10 | Naan innaikku nine hundred rupees tharen | 900 | today | |
| 11 | Naan Thursday-ku one thousand two hundred rupees kattuven | 1200 | Thursday | |
| 12 | Naan Sunday-ku aayiram rupaai tharen | 1000 | Sunday | |
| 13 | Naan Tuesday-ku four thousand rupees pay pannuren (TV or fan on) | 4000 | Tuesday | tv on |
| 14 | (Language: English India) I will pay five thousand rupees on Friday | 5000 | Friday | |

I expect some of these to fail (for example the ordinals "fifth" and "twentieth" are barely covered). That is the point.
