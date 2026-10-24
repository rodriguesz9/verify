"""Bounded wall-clock budgets. More time never counts as factual evidence.

Every phase uses its caller's remaining time; these are ceilings, not fixed
delays. Keep the browser margin above text + URL retrieval/persistence. Media
retains its separately tested budgets and never inherits new paid attempts.
"""

MAX_MODEL_WAIT_SECONDS = 120
TEXT_PIPELINE_WAIT_SECONDS = 420
TEXT_PARALLEL_WAIT_SECONDS = 150
SOURCE_RETRIEVAL_WAIT_SECONDS = 145
RESEARCH_PLAN_WAIT_SECONDS = 60
RESEARCH_FOLLOWUP_RESERVE_SECONDS = 30
COMPARISON_WAIT_SECONDS = 240
