// The decision-side contract: what the screener flags, what the agent pipeline
// concludes about it, and how that conclusion is scored after the fact.
// Terms are defined in CONTEXT.md; these types are the wire shapes for them.
//
// Raw numbers only, per the numeric wire contract — percentages are numbers
// rounded to two decimals, never display strings.

/** The call a Decision makes. Uppercase per the glossary, and deliberately
    distinct from `TradeSide` — that is an order side sent to Alpaca. */
export type Action = "BUY" | "SELL" | "HOLD"

/** The pipeline's own confidence in a Decision. */
export type Conviction = "low" | "medium" | "high"

/** Where a Decision stands with the executor. A Decision is never re-analyzed;
    only its status and outcome move after it is written. */
export type DecisionStatus = "pending" | "executed" | "skipped" | "expired"

/** The condition that made a ticker a Candidate, with the values that fired it. */
export interface Trigger {
  /** Screener-defined identifier, e.g. "volume_spike". */
  name: string
  /** The observed value. */
  value: number
  /** The value that had to be crossed for the trigger to fire. */
  threshold: number
}

/** A ticker the screener flagged on a given date as worth analyzing.
    Says nothing about direction. */
export interface Candidate {
  ticker: string
  /** ISO date (YYYY-MM-DD) — the trading day the screener ran over. */
  asOfDate: string
  triggers: Trigger[]
  /** 1 = most worth analyzing. Ranks attention, not conviction. */
  rank: number
  /** False for a Skipped Candidate — the control group, kept deliberately. */
  analyzed: boolean
}

/** The realized result of a Decision, measured after the fact. Null until the
    horizon has passed and the evaluation job has filled it in. */
export interface Outcome {
  return1dPct: number | null
  return5dPct: number | null
  return20dPct: number | null
  /** Return relative to the benchmark (SPY). */
  alpha1dPct: number | null
  alpha5dPct: number | null
  alpha20dPct: number | null
  /** ISO timestamp of the measurement, null while unmeasured. */
  measuredAt: string | null
}

/** What produced a Decision, recorded so outcomes can be attributed to it. */
export interface ModelConfig {
  provider: string
  deepModel: string
  quickModel: string
  debateRounds: number
}

/** Token spend for one Analysis Run. */
export interface RunCost {
  inputTokens: number
  outputTokens: number
  estimatedUsd: number
}

/** The pipeline's recorded output for one ticker on one date. A record, not an
    order — it may never be executed, and it is immutable once written. */
export interface Decision {
  id: string
  ticker: string
  /** ISO date (YYYY-MM-DD) — the trading day the Decision is about. */
  asOfDate: string
  /** ISO timestamp the record was written. */
  createdAt: string
  /** The triggers carried over from the Candidate this Decision came from. */
  triggers: Trigger[]
  action: Action
  conviction: Conviction
  /** Short natural-language rationale. */
  thesis: string
  /** Pointer to the stored agent reports, which live outside the database. */
  reportsRef: string | null
  modelConfig: ModelConfig
  cost: RunCost
  status: DecisionStatus
  outcome: Outcome | null
}
