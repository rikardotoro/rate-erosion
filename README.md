# rate-erosion

[![CI](https://github.com/rikardotoro/rate-erosion/actions/workflows/ci.yml/badge.svg)](https://github.com/rikardotoro/rate-erosion/actions/workflows/ci.yml)

**You negotiated −8%. You paid +3%. Here is where it went.**

A negotiated rate reduction is a headline, not an outcome. Over the contract
term it erodes — the base gets quietly over-billed, surcharges creep, a
peak-season charge appears, the exchange rate moves, and your traffic drifts
toward the expensive lane. None of that shows up in a report that compares
"contracted rate" to "contracted rate". This tool reads your cost lines,
decomposes the gap between what you signed and what you actually paid, and
then answers the question that decides whether procurement did a good job:
**how did you do against the market?**

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/charts/waterfall-dark.svg">
  <img alt="Waterfall chart of per-shipment cost: a contracted base of 2,199 dollars builds up through base rate creep, bunker surcharge, terminal handling, peak season surcharge and documentation fees to a realised all-in cost of 3,175 dollars." src="docs/charts/waterfall-light.svg" width="760">
</picture>

## The 30-second version

```bash
uvx --from git+https://github.com/rikardotoro/rate-erosion rate-erosion --demo
```

<!-- BEGIN OUTPUT -->
```
Per shipment, 2022-04:2022-06   
┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ Step            ┃ $ / shipment ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│ Contracted base │        2,189 │
│ Base rate creep │          +50 │
│ BAF             │         +326 │
│ THC             │         +235 │
│ PSS             │         +200 │
│ LSS             │         +130 │
│ DOC             │          +45 │
│ Realised all-in │        3,175 │
└─────────────────┴──────────────┘
 Total spend change 
┏━━━━━━━━┳━━━━━━━━━┓
┃ Effect ┃       $ ┃
┡━━━━━━━━╇━━━━━━━━━┩
│ Volume │ -14,003 │
│ Price  │ +55,948 │
│ Mix    │ +16,258 │
│ Fx     │  -5,504 │
│ Total  │ +52,700 │
└────────┴─────────┘

Realised cost per shipment moved +13.4% (183 shipments in 2021-01:2021-03, 178 
in 2022-04:2022-06).
The market (PPI: Deep Sea Freight Transportation (BLS)) moved +50.2% over the 
same window — you outperformed by 36.8% points.
All-in per shipment stepped +9.8% in 2021-08 (2,851 → 3,131).
All-in per shipment stepped -6.0% in 2021-11 (3,131 → 2,942).
All-in per shipment stepped +8.0% in 2022-04 (2,942 → 3,176).
Component shuffle: BAF and LSS move in opposition (correlation -1.00) while 
their sum barely moves. Money is being relabelled, not saved.
```
<!-- END OUTPUT -->

Three answers in one screen: **where** the money went (the waterfall),
**why** total spend moved (volume, price, mix, FX — summing exactly to the
total, no unexplained residual), and **whether to be angry about it** (the
market verdict).

## Why "contracted vs paid" is the wrong comparison

Two separate mistakes hide in most freight cost reviews:

1. **The gap is treated as one number.** "We're paying 14% more per box" is
   not actionable. *Which part* is the carrier over-billing the base, which
   part is bunker, which part is your own lane mix shifting? Each has a
   different owner and a different fix. The waterfall above splits the demo's
   gap into six named pieces.

2. **The change is compared to nothing.** In the demo, realised cost per
   shipment rises 14% over the contract term — sounds like a procurement
   failure. Over the same window the market rose 50%. Locking a contract that
   only leaked 14 points in that market was an excellent outcome, and a
   report that can't say so punishes the people who earned it. Erosion and
   outperformance are different questions; you need both answers.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/charts/market-dark.svg">
  <img alt="Line chart indexing your per-shipment cost against the Deep Sea Freight PPI, both starting at 100 in January 2021. Your cost ends at 114 while the market ends at 150 — the gap is the outperformance." src="docs/charts/market-light.svg" width="760">
</picture>

There is a third, quieter mistake: **letting FX and mix pollute the price
line.** A euro-denominated handling charge that didn't change in euros is not
a rate increase, and more shipments on the expensive lane is not a carrier
price rise. The tool revalues both periods at constant exchange rates and
splits mix from price with the standard variance identity, so each effect
lands in its own row — and the four rows sum to the total change exactly.
You don't have to supply the exchange rates: when a line has a currency but
no `fx_rate`, the tool looks up the Federal Reserve's actual daily rate for
that date (15 major currencies, cached locally). In the demo, the FX row is
the real 2021-22 euro slide showing up in euro-billed handling charges.

## The patterns underneath

Two more questions the tables above cannot answer, so the tool checks for
them on the full history:

**When did the rate actually move?** The monthly all-in is segmented into
regimes with a changepoint detector, so instead of "costs went up" you get
dates and magnitudes: in the demo, +9.8% in August 2021, back down −6.0% in
November, up again +8.0% in April 2022 — which is the peak-season surcharge
switching on and off, caught from the numbers alone.

**Is money being relabelled?** The classic way around a rate cap is to lower
one charge and introduce another for the same amount. The all-in stays flat,
the cap is technically honoured, and a report that only tracks totals sees
nothing. The signature is mechanical: two components whose month-over-month
moves cancel each other. In the demo, a new LSS code appears in October 2021
for exactly what BAF gave up, and the tool calls it out:

> Component shuffle: BAF and LSS move in opposition (correlation −1.00) while
> their sum barely moves. Money is being relabelled, not saved.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/charts/relabel-dark.svg">
  <img alt="Line chart of monthly bunker-related charges per shipment. The BAF line drops sharply in October 2021 exactly when a new LSS line appears, while the dashed line of their sum continues smoothly upward as if nothing happened." src="docs/charts/relabel-light.svg" width="760">
</picture>

Neither check fits in a spreadsheet formula, which is why they are in the
tool rather than in the recipes below.

## Do this in your own tools

You don't need this tool to stop reporting one blended number. The pieces are
one formula away in whatever you already use:

**Excel**

Per-shipment cost of each charge type — a pivot of amount by charge code, or:

```
=SUMIFS(amount, charge_code, "BAF") / SUMPRODUCT(1/COUNTIF(shipments, shipments))
```

Build it once per period and the waterfall is a bar chart away.

**Power BI (DAX)**

```
Price Effect :=
SUMX(
    VALUES(Shipments[lane]),
    [Cur Shipments] * ([Cur Unit Cost] - [Base Unit Cost])
)
```

Mix and volume follow the same `SUMX` pattern with the reference costs
swapped — this is textbook price/volume/mix variance, which is exactly the
point: it's a core BI technique that freight reporting rarely uses.

**SQL**

```sql
SELECT charge_code,
       SUM(amount) / COUNT(DISTINCT shipment) AS per_shipment
FROM cost_lines
WHERE date BETWEEN '2022-04-01' AND '2022-06-30'
GROUP BY charge_code
ORDER BY per_shipment DESC;
```

Run it for both periods and subtract.

None of these stop FX or lane mix from polluting the price line, and none of
them benchmark you against the market — isolating the effects exactly and
attaching the FRED verdict is what the tool adds.

## Five ways to get this wrong

Each is a real mistake from real cost reviews, and each has a test proving
the failure mode:

1. **Reaching for the Baltic Dry Index because it's the famous one.** It
   measures dry bulk — iron ore, grain, coal — not containers. The tool
   refuses it, by name, and tells you why.
   → [`tests/test_benchmark.py::test_baltic_dry_index_is_refused_with_explanation`](tests/test_benchmark.py)

2. **Booking a mix shift as a price change.** If per-lane prices are flat and
   your volume moved to the dear lane, the price effect must be zero.
   → [`tests/test_decompose.py::test_mix_shift_is_not_booked_as_price`](tests/test_decompose.py)

3. **Booking FX movement as a rate change.** A charge that didn't move in its
   own currency is not a carrier increase.
   → [`tests/test_decompose.py::test_fx_movement_is_not_a_rate_change`](tests/test_decompose.py)

4. **Comparing your rate change to nothing.** +14% is a disaster in a flat
   market and a triumph in 2021-22. The verdict is relative or it is
   meaningless.
   → [`tests/test_benchmark.py::test_verdict_reports_relative_points`](tests/test_benchmark.py)

5. **Trusting a flat all-in.** Components can be relabelled underneath it —
   one charge down, a new one up by the same amount — which is how a rate cap
   gets managed instead of honoured. The tool tests components for offsetting
   movement.
   → [`tests/test_patterns.py::test_planted_shuffle_is_detected`](tests/test_patterns.py)

## Run it

```bash
uvx --from git+https://github.com/rikardotoro/rate-erosion rate-erosion --demo
uvx --from git+https://github.com/rikardotoro/rate-erosion rate-erosion \
  --data cost_lines.csv --contract contract.csv \
  --baseline 2025-01:2025-03 --current 2026-04:2026-06
```

**Cost lines CSV** (column names auto-detected from common aliases; force any
mapping with `--map canonical=your_column`):

| Column | Required | Meaning |
|---|---|---|
| `shipment` | yes | Shipment / BL / container reference |
| `date` | yes | Charge or invoice date |
| `lane` | yes | Trade lane the shipment moved on |
| `charge_code` | yes | BAS, BAF, THC, PSS… base codes fold into "base" |
| `amount` | yes | Charge amount in its own currency |
| `currency` | no | Defaults to USD |
| `fx_rate` | no | USD per unit of line currency. Omit it and the tool fills it from the Fed's daily H.10 rates by line date; supply it only to override |

**Contract CSV**: `lane`, `base_rate` (per shipment, contract currency).

Options: `--baseline`/`--current` pick the comparison windows (default:
first vs last three months of the data); `--benchmark` picks the FRED series
(`PCU483111483111` deep-sea PPI by default, `PCU4883204883208` container
handling, `FRGSHPUSM649NCIS` Cass shipments, or `none`); `--json` for
machine-readable output.

## What this doesn't do

- **It does not tell you whether a surcharge was legitimate.** It tells you
  which surcharge ate your savings; arguing about it is your job.
- **It needs a contracted rate per lane.** No contract file, no waterfall —
  the tool has nothing to compare against.
- **Automatic FX assumes your contract currency is USD.** Billing in a
  non-USD home currency works, but you must supply the `fx_rate` column
  yourself — the Fed's rates are quoted against the dollar.
- **The FRED benchmarks are US PPI-based proxies, not lane-level spot
  rates.** Professionals use SCFI, WCI or FBX for lane pricing; those are
  subscription products whose free tiers cover headline values only, so this
  tool uses genuinely free series and says so.
- **The demo cost lines are synthetic.** Real invoice-level freight data is
  effectively never published, so [`scripts/make_demo.py`](scripts/make_demo.py)
  generates a realistic erosion story with a fixed seed and
  [`examples/SOURCE.md`](examples/SOURCE.md) discloses it plainly. The market
  benchmark and the exchange rates in the demo are **real** — the actual BLS
  Deep Sea Freight PPI, which really did rise 50% over the demo's 2021-22
  contract term, and the Fed's actual daily EUR/USD rates.

## Is any of this actually tested?

All of it. Every claim in this README is enforced by a test — each trap in
"Four ways to get this wrong" links to the test that proves it, the
decomposition's exactness (effects sum to the total, no residual) is itself a
test, and the demo output above is generated by running the tool, never
pasted in. The suite runs in CI on every push, against Python 3.11 and 3.12.

<details>
<summary><strong>The full test list</strong> — regenerated by <code>scripts/render_readme_output.py</code>, so it can't drift</summary>

<!-- BEGIN TESTS -->
```
60 passed

tests/test_benchmark.py::test_default_series_is_registered PASSED
tests/test_benchmark.py::test_resolve_accepts_a_known_id PASSED
tests/test_benchmark.py::test_baltic_dry_index_is_refused_with_explanation PASSED
tests/test_benchmark.py::test_unknown_series_lists_the_supported_ones PASSED
tests/test_benchmark.py::test_load_series_parses_fredgraph_csv PASSED
tests/test_benchmark.py::test_pct_change_uses_asof_values PASSED
tests/test_benchmark.py::test_verdict_reports_relative_points PASSED
tests/test_cli.py::test_cli_runs_and_reports PASSED
tests/test_cli.py::test_cli_json_output_is_valid PASSED
tests/test_cli.py::test_cli_refuses_baltic_dry PASSED
tests/test_data.py::test_detects_canonical_names PASSED
tests/test_data.py::test_detects_common_aliases PASSED
tests/test_data.py::test_override_beats_detection PASSED
tests/test_data.py::test_missing_required_column_names_the_column PASSED
tests/test_data.py::test_base_codes_are_recognised_case_insensitively PASSED
tests/test_data.py::test_load_defaults_currency_and_fx PASSED
tests/test_data.py::test_unparseable_date_names_the_row PASSED
tests/test_data.py::test_non_numeric_amount_names_the_row PASSED
tests/test_data.py::test_load_contract PASSED
tests/test_data.py::test_contract_rejects_non_positive_rate PASSED
tests/test_decompose.py::test_effects_sum_exactly_to_total_change PASSED
tests/test_decompose.py::test_mix_shift_is_not_booked_as_price PASSED
tests/test_decompose.py::test_fx_movement_is_not_a_rate_change PASSED
tests/test_decompose.py::test_pure_volume_change PASSED
tests/test_decompose.py::test_new_lane_in_current_period_does_not_crash PASSED
tests/test_demo_data.py::test_demo_files_are_small PASSED
tests/test_demo_data.py::test_demo_loads_and_spans_the_contract_term PASSED
tests/test_demo_data.py::test_demo_is_reproducible PASSED
tests/test_demo_data.py::test_offline_fred_slice_loads PASSED
tests/test_demo_data.py::test_demo_shuffle_is_detected PASSED
tests/test_fx.py::test_usd_lines_fill_with_one PASSED
tests/test_fx.py::test_eur_fills_asof_the_line_date PASSED
tests/test_fx.py::test_units_per_usd_series_is_inverted PASSED
tests/test_fx.py::test_user_supplied_fx_is_never_touched PASSED
tests/test_fx.py::test_unknown_currency_says_how_to_fix_it PASSED
tests/test_fx.py::test_date_before_series_start_raises PASSED
tests/test_patterns.py::test_monthly_matrix_is_per_shipment PASSED
tests/test_patterns.py::test_planted_shuffle_is_detected PASSED
tests/test_patterns.py::test_independent_movement_is_not_a_shuffle PASSED
tests/test_patterns.py::test_joint_increases_are_not_a_shuffle PASSED
tests/test_patterns.py::test_too_few_months_returns_none PASSED
tests/test_patterns.py::test_changepoints_find_a_single_step PASSED
tests/test_patterns.py::test_changepoints_ignore_pure_noise PASSED
tests/test_patterns.py::test_changepoints_find_two_steps PASSED
tests/test_patterns.py::test_rate_regimes_report_step_direction PASSED
tests/test_periods.py::test_parse_period_is_month_inclusive PASSED
tests/test_periods.py::test_parse_period_rejects_garbage PASSED
tests/test_periods.py::test_explicit_periods_select_rows PASSED
tests/test_periods.py::test_default_periods_are_first_and_last_three_months PASSED
tests/test_periods.py::test_empty_period_raises PASSED
tests/test_report.py::test_analysis_counts_and_change PASSED
tests/test_report.py::test_verdict_included_when_market_given PASSED
tests/test_report.py::test_to_dict_is_json_serialisable PASSED
tests/test_smoke.py::test_version_is_exposed PASSED
tests/test_smoke.py::test_unknown_series_error_is_a_rate_erosion_error PASSED
tests/test_waterfall.py::test_shipment_count_is_distinct_references PASSED
tests/test_waterfall.py::test_base_codes_fold_into_base_category PASSED
tests/test_waterfall.py::test_waterfall_steps_sum_to_realised PASSED
tests/test_waterfall.py::test_surcharges_sorted_by_impact PASSED
tests/test_waterfall.py::test_lane_missing_from_contract_is_an_error PASSED
```
<!-- END TESTS -->

</details>

## Licence

MIT.
