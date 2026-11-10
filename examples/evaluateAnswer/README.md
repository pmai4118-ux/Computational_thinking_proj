# Synthetic evaluation examples

- `sampleInput.json` contains an authored Python question, four competency rubrics with three declared score levels each, and a submitted answer. The scoring engine is not limited to these levels.
- `sampleReview.json` is a recorded interpretation bound to that exact input hash. It demonstrates and checks scoring logic; it is not a live Gemini result.
- `alternativeAnswer.txt` presents a correct brute-force method. The question does not require linear time, so a different algorithm is not automatically wrong. Use it for manual review or with the configured Gemini provider.

These examples have not been independently reviewed or approved as a question bank. The system reads submitted code as text and never executes it.

```powershell
.\.venv\Scripts\python.exe -m source.main --input examples/evaluateAnswer/sampleInput.json --answerFile examples/evaluateAnswer/alternativeAnswer.txt --provider gemini
```

After a live run, a human reviewer should inspect each criterion check and supporting evidence. The recorded review cannot be reused for `alternativeAnswer.txt`; its input hash will not match.
