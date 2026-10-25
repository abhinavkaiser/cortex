# Cortex technical bridge lab pack

Uses Python 3.10+ and the standard library only. No API key, network call,
private dataset, package installation or model download is required.

1. Extract the ZIP and open a terminal in its directory.
2. Run `python3 -m unittest -v` (Windows: `py -m unittest -v`).
3. Run `python3 retrieval.py` and preserve the development result.
4. Improve `retrieve` on development questions only. Keep the data fixed.
5. Run `python3 retrieval.py --test` once after selecting a change. Record
   wins, regressions, unanswerable queries and the limitations of this tiny set.
6. Run `python3 classifier.py`; use validation to choose a threshold. Do not
   tune against the final test result. Explain which error is more costly.
7. Inspect `tools.py`: try an unauthorized call and a duplicate refund key.

Deliver a short report with commands, original result, one change, new result,
per-case failure analysis and a limitation. A good result is reproducible and
honest; it need not beat the baseline. The retrieval labels and test questions
are visible for learning: voluntarily keep test cases out of development.
This is not a hidden examination or evidence of production readiness.

Extension: compare an embedding model on the same data. Follow its own input
conventions, document dependencies and measure any cost/latency change. Do not
claim a semantic retriever wins until you have measured it.

## Advanced reproduction project

Run `python3 advanced_training.py --epochs 100 --rate .1 --regularization .01`.
Preserve the JSON output, dataset hash, normalization and split information.
Compare one changed setting using validation. Do not select a winner from test
results. Report confusion counts, a null/failure result and the limits of a tiny
synthetic dataset. The online project executes your bounded configuration and
reviews your report/code; it does not execute uploaded arbitrary Python.
