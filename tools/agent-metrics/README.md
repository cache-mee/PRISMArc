# agent-metrics

Measure what an agent run cost, took, and did — as small independent providers behind one caller.

    metrics.py capabilities
    metrics.py run --want cost_usd,total_tokens --label task=901 -- claude -p "..."
    metrics.py report --by agent
    metrics.py --self-test

## Why it is split

Every provider answers ONE data source, not one metric. Six metrics that all come from a
single OTLP export are one provider, because splitting them would mean six receivers and
six runs of your command. The boundary that matters is *where the number comes from*.

## The contract

A provider is an executable script in `providers/`. It is never imported. It answers two
verbs, and the caller discovers it by globbing the directory — adding one is dropping a
file in, removing one is deleting a file.

    <provider> capabilities
      -> {"name": str, "phase": "wrap"|"parse"|"around"|"query",
          "provides": [metric...], "dimensions": [str...]}

    <provider> collect --request <file.json>              # phase parse / around / query
    <provider> wrap    --request <file.json> -- <cmd...>  # phase wrap only

The request file holds:

    {"want": [metric...], "labels": {...}, "cwd": str,
     "out": "<path the provider writes its rows to>",
     "stdout_file": "<child stdout; written by wrap, read by parse>",
     "when": "before"|"after"}          # around providers are called twice

A provider writes `{"rows": [...]}` to `request["out"]`. It writes NOTHING to stdout except,
for a wrap provider, the child's own output relayed through. Exit code of a wrap provider is
the child's own.

## The four phases, and why there are four

    wrap     Owns the child process. AT MOST ONE. It is the only thing that can set the
             child's environment, which is what telemetry needs, so it also captures the
             child's stdout for everyone else.
    parse    Reads the captured stdout after the child exits. Owns no process.
    around   Called twice, `when=before` and `when=after`. For state that is observed by
             looking at the world rather than at the process, such as git.
    query    Reads a durable artifact. Needs no child at all.

## Canonical metric names

Providers must use these spellings, so two providers reporting the same thing collide
visibly instead of quietly producing two columns.

    input_tokens  output_tokens  total_tokens  cache_read_tokens  cache_creation_tokens
    cost_usd  execution_ms  api_ms  turns
    files_changed  lines_added  lines_removed
    tests_total  tests_passed  build_status
    rework  human_interventions  outcome

## The ledger

`~/.claude/metrics/ledger.jsonl`, append-only, one row per (provider, dimension-set).
Override with `--ledger` or `$AGENT_METRICS_LEDGER`.

## Adding a provider

Write the file, make it answer `capabilities`, give it a `--self-test`. The caller's
`--self-test` runs every provider's own, so a broken provider fails the suite without the
caller knowing anything about it.

---

@author Samson Paul, samson.paul@experionglobal.com
