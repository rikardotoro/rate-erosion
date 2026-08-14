# rate-erosion

[![CI](https://github.com/rikardotoro/rate-erosion/actions/workflows/ci.yml/badge.svg)](https://github.com/rikardotoro/rate-erosion/actions/workflows/ci.yml)

**You negotiated −8%. You paid +3%. Here is where it went.**

You negotiate a rate reduction with your carrier, and a year later the invoices
say you are paying more than before. This happens constantly, and it is rarely
one big thing. The base rate gets billed a little high. The fuel surcharge
creeps. A "peak season surcharge" appears for a few months. A charge billed in
euros moves with the exchange rate. And your own shipments drift toward the
more expensive route. Each piece is small; together they eat the discount.

This tool reads your cost lines — one row per charge on each shipment — and
splits the gap between the rate you signed and the money you actually paid,
piece by piece. Then it answers the question that decides whether the
negotiation was actually good: **how did you do compared to the market?**

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/charts/waterfall-dark.svg">
  <img alt="Waterfall chart of per-shipment cost: a contracted base of 2,189 dollars builds up through base rate creep, fuel surcharge, terminal handling, peak season surcharge, low-sulphur surcharge and documentation fees to a realised all-in cost of 3,175 dollars." src="docs/charts/waterfall-light.svg" width="760">
</picture>

## The 30-second version

```bash
uvx --from git+https://github.com/rikardotoro/rate-erosion rate-erosion --demo
```

<!-- BEGIN OUTPUT -->
```
What one shipment cost you, Apr–Jun 2022      
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ Step                             ┃ $ / shipment ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│ Contracted base                  │        2,189 │
│ Base rate creep                  │          +50 │
│ BAF — fuel surcharge             │         +326 │
│ THC — terminal handling          │         +235 │
│ PSS — peak season surcharge      │         +200 │
│ LSS — low-sulphur fuel surcharge │         +130 │
│ DOC — documentation fee          │          +45 │
│ Realised all-in                  │        3,175 │
└──────────────────────────────────┴──────────────┘
Top row: the rate you negotiated. Bottom row: what you actually paid. Every line
in between is a piece of the gap.
  Why total spend changed, Jan–Mar 2021 →  
               Apr–Jun 2022                
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┓
┃ Reason                        ┃       $ ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━┩
│ Number of shipments (volume)  │ -14,003 │
│ What carriers charged (price) │ +55,948 │
│ Which lanes you used (mix)    │ +16,258 │
│ Exchange rates (FX)           │  -5,504 │
│ Total change                  │ +52,700 │
└───────────────────────────────┴─────────┘
The four reasons add up to the total exactly — nothing is left over.

Your cost per shipment moved +13.4% between the two periods (183 shipments, then
178).
The market (PPI: Deep Sea Freight Transportation (BLS)) moved +50.2% over the 
same time. You did 36.8% points better than the market.
Your all-in rate stepped +9.8% in Aug 2021 (2,851 → 3,131 per shipment).
Your all-in rate stepped -6.0% in Nov 2021 (3,131 → 2,942 per shipment).
Your all-in rate stepped +8.0% in Apr 2022 (2,942 → 3,176 per shipment).
Worth a look: BAF (fuel surcharge) and LSS (low-sulphur fuel surcharge) mirror 
each other month by month while their sum stays flat. That usually means money 
was relabelled between charge codes, not saved.
```
<!-- END OUTPUT -->

Three answers in one screen. The first table shows **where** the money went:
from the rate you negotiated at the top to what you actually paid at the
bottom, with every surcharge spelled out in between. The second shows **why**
your total spend changed, split into four reasons that add up exactly. The
last lines tell you **whether to be upset about it** — and in the demo, the
answer is no: costs rose 13%, but the market rose 50%.

## Two mistakes most cost reviews make

**Mistake 1: treating the gap as one number.** "We are paying 14% more per
shipment" doesn't tell anyone what to do. Is the carrier over-billing the
base rate? Is it fuel? Is it your own traffic moving to the expensive route?
Each of those has a different owner and a different fix, so the tool keeps
them apart.

**Mistake 2: comparing your costs to nothing.** In the demo, cost per
shipment rises 13% over the contract. On its own that looks like a failure.
But over the same 18 months the market price of ocean freight rose 50% — so
whoever locked that contract saved the company a fortune, and a report that
only shows "+13%" punishes them for it. The comparison uses a free public
index (the US producer price index for deep sea freight, from FRED), so
there is nothing to subscribe to.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/charts/market-dark.svg">
  <img alt="Line chart indexing your per-shipment cost against the Deep Sea Freight producer price index, both starting at 100 in January 2021. Your cost ends at 114 while the market ends at 150 — the gap is your outperformance." src="docs/charts/market-light.svg" width="760">
</picture>

There is a quieter third mistake: letting currency and route changes pollute
the numbers. A charge billed in euros that didn't change *in euros* is not a
price increase — the exchange rate moved, not the carrier. And more shipments
on an expensive route is not a rate rise either. The tool separates both out,
so the "price" line only ever contains actual price changes. You don't even
need to supply exchange rates: it looks up the Federal Reserve's real daily
rate for each line's date (15 major currencies, cached locally).

## What "the market" actually is here

Fair question, because it is not the index most people would name first.

The default benchmark is the **Producer Price Index for Deep Sea Freight
Transportation**, published by the US Bureau of Labor Statistics and served
through FRED. Every month the BLS asks ocean freight carriers what prices
they are actually charging for their services, and the index tracks how that
average moves. So "the market rose 50%" means: over the same window, carriers'
selling prices — as measured by a government statistical survey that has run
since 1988 — rose 50%. That is exactly the yardstick the verdict needs:
did carrier pricing broadly rise or fall while your contract ran, and by
roughly how much.

Why not the alternatives you may have heard of:

- **The Baltic Dry Index** is the famous one, and it is the wrong one. It
  tracks the cost of chartering ships that carry bulk goods — iron ore,
  grain, coal — not containers. Ask this tool for it and it will refuse and
  tell you why.
- **SCFI, WCI and FBX** are the indices freight professionals quote for
  container lane rates, and they are subscription products. The free versions
  give you today's headline, not the history, and their licences don't allow
  redistribution. This tool only uses data anyone can pull for free, so its
  results can be checked by anyone.

The PPI has honest limitations. It is US-centric, it averages all lanes and
carriers, it blends contract and spot business, and it is an index rather
than a dollars-per-container rate. That makes it useless for pricing a
specific lane — and perfectly adequate for judging the *direction and rough
size* of the market move behind your contract, which is all the verdict
claims. Two alternates ship in the registry (`--benchmark` accepts them): the
PPI for marine container handling, and the Cass Freight Index expenditures
series, which tracks total freight spend.

## The patterns underneath

Two things you can't see in a summary table, so the tool checks the full
month-by-month history for them:

**When did the rate actually move?** Instead of "costs went up", you get
dates and sizes. In the demo: up 9.8% in August 2021, back down 6% in
November, up 8% again in April 2022 — which is a peak-season surcharge
switching on and off, found from the numbers alone.

**Is money being relabelled?** A common way around a negotiated price cap:
lower one charge and introduce a new one for the same amount. The total stays
flat, the cap is technically respected, and a report that tracks only totals
sees nothing. The tool looks for pairs of charges that mirror each other
month after month. In the demo, a "new" low-sulphur surcharge appears in
October 2021 for exactly what the fuel surcharge gave up:

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/charts/relabel-dark.svg">
  <img alt="Line chart of monthly fuel-related charges per shipment. The fuel surcharge line drops sharply in October 2021 exactly when a new low-sulphur surcharge line appears, while the dashed line of their sum continues smoothly as if nothing happened." src="docs/charts/relabel-light.svg" width="760">
</picture>

When that happens, the tool says so in plain words: *money was relabelled
between charge codes, not saved.*

## Do this in your own tools

You don't need this tool to stop reporting one blended number. The basic
pieces are one formula away in whatever you already use:

**Excel** — a pivot of amount by charge code, per quarter, is already the
waterfall. Per-shipment cost of one charge type:

```
=SUMIFS(amount, charge_code, "BAF") / SUMPRODUCT(1/COUNTIF(shipments, shipments))
```

**Power BI (DAX)** — the price effect for each lane, which is the heart of a
price/volume/mix split:

```
Price Effect :=
SUMX(
    VALUES(Shipments[lane]),
    [Cur Shipments] * ([Cur Unit Cost] - [Base Unit Cost])
)
```

Mix and volume follow the same pattern with the reference values swapped.
This is a standard business-intelligence technique — the point is that
freight reporting almost never uses it.

**SQL** — cost per shipment by charge type for one period:

```sql
SELECT charge_code,
       SUM(amount) / COUNT(DISTINCT shipment) AS per_shipment
FROM cost_lines
WHERE date BETWEEN '2022-04-01' AND '2022-06-30'
GROUP BY charge_code
ORDER BY per_shipment DESC;
```

Run it for both periods and subtract.

What none of these do: keep exchange rates and route changes out of the price
line, benchmark you against the market, or catch the relabelling trick. Those
are the parts the tool adds.

## Five ways to get this wrong

These are real mistakes from real cost reviews. Each one has a test in this
repo that reproduces the failure:

1. **Reaching for the Baltic Dry Index because it's the famous one.** It
   tracks bulk goods — iron ore, grain, coal — not containers. The tool
   refuses it by name and explains why.
   → [`tests/test_benchmark.py::test_baltic_dry_index_is_refused_with_explanation`](tests/test_benchmark.py)

2. **Calling a route change a price change.** If per-lane prices are flat and
   your volume moved to the dear lane, the price effect must be exactly zero.
   → [`tests/test_decompose.py::test_mix_shift_is_not_booked_as_price`](tests/test_decompose.py)

3. **Calling a currency move a price change.** A charge that didn't move in
   its own currency is not a carrier increase.
   → [`tests/test_decompose.py::test_fx_movement_is_not_a_rate_change`](tests/test_decompose.py)

4. **Comparing your rate change to nothing.** +13% is a disaster in a flat
   market and a triumph in 2021-22. Without the market next to it, the number
   means nothing.
   → [`tests/test_benchmark.py::test_verdict_reports_relative_points`](tests/test_benchmark.py)

5. **Trusting a flat total.** Charges can be relabelled underneath it — one
   down, a new one up by the same amount. That is how a price cap gets
   managed instead of honoured.
   → [`tests/test_patterns.py::test_planted_shuffle_is_detected`](tests/test_patterns.py)

## Run it

```bash
uvx --from git+https://github.com/rikardotoro/rate-erosion rate-erosion --demo
uvx --from git+https://github.com/rikardotoro/rate-erosion rate-erosion \
  --data cost_lines.csv --contract contract.csv \
  --baseline 2025-01:2025-03 --current 2026-04:2026-06
```

**Cost lines CSV** — one row per charge on each shipment. Column names are
auto-detected from common aliases; force any of them with
`--map canonical=your_column`:

| Column | Required | Meaning |
|---|---|---|
| `shipment` | yes | Shipment / bill-of-lading / container reference |
| `date` | yes | Charge or invoice date |
| `lane` | yes | The route the shipment moved on |
| `charge_code` | yes | BAS, BAF, THC… base-rate codes are grouped as "base" |
| `amount` | yes | Charge amount, in its own currency |
| `currency` | no | Defaults to USD |
| `fx_rate` | no | Leave it out — the tool fills it from the Fed's daily rates |

**Contract CSV** — what you negotiated: `lane`, `base_rate` (per shipment).

Options: `--baseline` and `--current` pick the two periods to compare
(default: first vs last three months of your data). `--benchmark` picks the
market index — the deep-sea producer price index by default, `none` to skip.
`--json` for machine-readable output.

## What this doesn't do

- **It won't tell you whether a surcharge was legitimate.** It tells you
  which one ate your savings; the conversation with the carrier is your job.
- **It needs your contracted rate per lane.** Without the contract file there
  is nothing to compare against.
- **The market index is a broad US proxy, not your lane's spot rate.** The
  indices professionals quote for lane pricing (SCFI, WCI, FBX) are
  subscription products, so this tool uses genuinely free government data
  and says so.
- **The demo cost lines are synthetic.** Real invoice data is never published
  openly, so [`scripts/make_demo.py`](scripts/make_demo.py) generates a
  realistic story with a fixed seed and
  [`examples/SOURCE.md`](examples/SOURCE.md) discloses it. The market data in
  the demo is real — the actual index, which really did rise 50% over the
  demo's 2021-22 term — and so are the exchange rates.

## Is any of this actually tested?

Yes. The exactness claim — four effects that sum to the total with nothing
left over — is itself a test. So is the planted relabelling in the demo:
if the detector stopped catching it, CI would fail. Every trap above names
its test, the demo output is produced by running the tool, and the suite
runs on every push against Python 3.11 and 3.12.

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
