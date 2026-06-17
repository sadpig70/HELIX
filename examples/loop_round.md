# Example — one HELIX loop turn

A walk-through of `core.helix_loop.next_action` over a few states, showing the
spiral advancing (never collapsing to a circle).

```text
state                                                 -> action          why
----------------------------------------------------------------------------------------
{corpus_size: 0}                                      -> RUN_EXPLORE     corpus immature -> scan world
{last_engine: explore, corpus_size: 3,
 diversity: {triggered: false}}                       -> RUN_EXPLOIT     fresh assets -> recombine (compound)
{last_engine: exploit, corpus_size: 4,
 pending_implemented_winner: true,
 winner_in_ledger: false}                             -> RECORD_CONSUMED implemented winner -> ledger (base-pairing)
{last_engine: exploit, corpus_size: 4,
 diversity: {triggered: true}}                        -> REFRESH_INPUTS  diversity triggered -> repair before generating
{last_engine: exploit, corpus_size: 5,
 diversity: {triggered: false}}                       -> RUN_EXPLORE     balance the strands
```

Reading: the loop never just "selects the best again". It (1) closes provenance
when a winner is built (base-pairing -> corpus), (2) repairs inputs when outputs
start converging (the DNA-repair gate), and (3) alternates explore/exploit so the
two strands keep feeding each other. That ordering is *why* the closed loop keeps
rising instead of flattening into a circle.
