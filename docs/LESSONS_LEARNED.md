# Lessons Learned

Mistakes this project has already made, so the next person or agent does not repeat them. Every agent working here reads this file first and adds to it before finishing (see `AGENTS.md`).

Format for new entries: a heading `### L<n>. <one-line rule>`, then **What happened**, **Why it mattered**, **Check that would have caught it**.

---

### L1. Never name a value after a method that was not run

**What happened:** band gaps were labelled "HSE06+SOC", a pair-spring model was called a "dynamical matrix", a closed-form expression was called an "11-image NEB". None of those calculations existed.
**Why it mattered:** every downstream result looked validated. Experts would dismiss the whole repository on first read.
**Check that would have caught it:** a provenance tag on every number (`MP_DFT`, `LITERATURE`, `COMPUTED_HERE`, `MLIP`, `HEURISTIC`, `ASSUMED`) and a grep for method names in fields whose provenance is `HEURISTIC`.

### L2. Validate upstream before building downstream

**What happened:** versions 4 to 8 added optics, LCOE, bifacial models, string matching and a commercialization plan on top of band gaps that had never been compared with a single measurement.
**Why it mattered:** the estimate was off by 0.45 eV on average and by 0.8 eV for CuBiS2; everything stacked on it was meaningless.
**Check that would have caught it:** a benchmark against measured values, with an error figure, required before any new downstream stage is added.

### L3. Re-implementing a formula is not verification

**What happened:** the "independent verifier" copied the primary formulas, so agreement was guaranteed. SHA-256 digests were described as signatures.
**Why it mattered:** "100% verified" meant only that the arithmetic was typed twice.
**Check that would have caught it:** count a check as verification only if it uses a different method or data source (experiment, a second code, a published table).

### L4. A gate that cannot fail is not a gate

**What happened:** a phonon gate was clipped so it always passed; a positive spring model always reported zero imaginary modes; a contrastive margin was positive for any labelling.
**Why it mattered:** the funnel looked selective while selecting nothing.
**Check that would have caught it:** a unit test per gate that feeds it an input which must fail.

### L5. Compare the error bar with the decision it supports

**What happened:** candidates were selected on target windows 0.15 to 0.20 eV wide using a gap estimate with a 0.44 eV error.
**Why it mattered:** the best possible "probability in window" was about 0.18. Rankings inside the window were noise.
**Check that would have caught it:** report window probability next to every selection, and state the maximum achievable probability for the error bar in use.

### L6. Wire calibration into the code path, then test that it is used

**What happened:** a calibration pass fitted a better model and wrote a literature table, but the pipeline kept using the old formula and never read the table. Only the error bar was copied across, and it was a mean absolute error used as a standard deviation.
**Why it mattered:** CuBiS2 (measured 1.65 eV) stayed listed as a 0.75 eV bottom-cell finalist after the measurement was in the repository.
**Check that would have caught it:** a test asserting that every estimated value in the outputs equals the calibrated model's prediction, and that a known measured value overrides the estimate.

### L7. Do not apply a threshold derived from an estimate as if it were a measurement

**What happened:** optical-efficiency thresholds (which are a deterministic function of the gap) rejected candidates whose gap was only estimated, re-imposing a hard window at a point value after the window gate had been made probabilistic.
**Why it mattered:** it silently undid the uncertainty handling.
**Check that would have caught it:** for each gate, list its inputs' provenance; gates on derived quantities only reject when the inputs are measured or computed.

### L8. Generate result tables; never pin them by hand

**What happened:** the auditor and tests pinned dozens of numbers from one run (funnel counts, efficiencies, pair counts). Every legitimate fix broke them, and the README drifted from the outputs.
**Why it mattered:** agents were tempted to edit numbers to make checks pass, and readers saw stale figures.
**Check that would have caught it:** generate README result blocks from the output files; tests assert consistency between files, not specific values, except for external reference values.

### L9. Pull-request descriptions are claims too

**What happened:** an agent's pull-request description named finalists that were not in the outputs and misquoted a formula and an error figure, while the committed files were correct.
**Why it mattered:** the owner reads the description, not the JSON.
**Check that would have caught it:** generate the numbers in a pull-request description from the committed outputs, or quote them with file paths.

### L10. Agent effort is not evidence

**What happened:** fourteen hours of agent work produced "13 agents", "debates", "consensus" and "kill-gates", all written as text with no tool calls behind them.
**Why it mattered:** volume and confident tone substituted for one real calculation.
**Check that would have caught it:** a claim enters the README only with a link to the code path, data file or job output that produced it.
