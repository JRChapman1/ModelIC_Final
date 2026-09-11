# ModelIC feature parity plan

This plan is to make the ModelIC repo the main codebase while preserving the functionality of the older legacy repos.

The short version:
- Keep ModelIC as the base project.
- Treat the older v0.1.x and modelic_web code as the feature reference set.
- Port only the functionality that is still needed, rather than copying the whole legacy codebase blindly.

## 1. Goal

Ensure ModelIC can do everything the older repos do, including:
- pricing and valuation of life and annuity products
- mortality, interest-rate and policy projection logic
- asset and liability modelling
- stress and sensitivity testing
- liability matching / SCR-type metrics
- reporting and output generation
- easy web or UI use if needed

## 2. What ModelIC already has

ModelIC already has the strongest base of the repos reviewed:
- core pricing and cashflow machinery
- mortality table support
- yield curve and curve helpers
- product types for:
  - annuity
  - endowment
  - life assurance
  - pure endowment
- pricing engine
- expense engine
- tests covering core functionality
- SII matching adjustment work already started

This is a good foundation for a modern actuarial engine.

## 3. What the older repos still provide

The older repos add useful business functionality that is not yet clearly represented in ModelIC:

### Legacy modelic v0.1.x strengths
- balance sheet and solvency calculations
- asset portfolio / bond portfolio logic
- ERM / LTM modelling
- with-profits and bonus features
- more detailed stress testing and scenario analysis
- data-generation and input handling for larger model runs
- output dashboards and CSV reports
- legacy risk measures and actuarial reporting

### modelic_web / ModelIC3 strengths
- web app front-end and interactive output flow
- easier user-driven scenario exploration and charts
- simulation-style running of insurance company projections
- business-style “company model” orchestration

## 4. Recommendation

Use ModelIC as the product codebase, but keep the legacy repos as a feature inventory.

Do not merge the whole legacy codebase. Instead:
- keep the good modern package layout from ModelIC
- port the missing actuarial features from legacy repos one by one
- keep tests for each migration item

## 5. Required work: phased TODO list

### Phase 1: Foundation and parity check

#### P1 - Build a feature inventory
- [ ] Create a checklist of every legacy feature still required
- [ ] Mark each item as: Required / Optional / Nice-to-have
- [ ] Confirm which items are already in ModelIC
- [ ] Attach file / test references for each legacy item

#### P1 - Define the canonical modelling interfaces
- [ ] Agree on a common model contract for products, curves, mortality, cashflows, and portfolios
- [ ] Standardise input/output types across modules
- [ ] Define how "policy", "portfolio", "projection", and "valuation" objects are represented

#### P1 - Add a single test runner for parity checks
- [ ] Keep a regression suite for the old models
- [ ] Add a test that compares ModelIC outputs with a legacy benchmark for the same scenario
- [ ] Record accepted tolerances for valuation outputs

---

### Phase 2: Core actuarial parity

#### P1 - Mortality and projection completeness
- [ ] Verify all mortality table operations needed by legacy models are covered
- [ ] Support age-based and duration-based projection logic
- [ ] Support deferred benefit and policy-year logic if used in legacy output
- [ ] Add tests for survival, death, and in-force probabilities

#### P1 - Interest rate and discount curve parity
- [ ] Add or confirm support for:
  - spot curves
  - zero curves
  - forward curves
  - real/nominal conversions
  - basis adjustments and spreads
- [ ] Confirm the curve API matches legacy assumptions for pricing and valuation

#### P1 - Cashflow generation parity
- [ ] Check all legacy cashflow patterns are represented:
  - premium cashflows
  - benefit cashflows
  - surrender / maturity / death benefits
  - policy expenses
  - deferred and contingent cashflows
- [ ] Ensure time indexing is consistent across products

#### P1 - Product parity
- [ ] Add or complete product support for legacy product formulas not yet in ModelIC
- [ ] Confirm annuity pricing and projections are aligned with older outputs
- [ ] Confirm life assurance pricing under mortality and discounting matches legacy behaviour
- [ ] Confirm endowment and pure endowment cases are fully covered

---

### Phase 3: Asset and liability framework parity

#### P1 - Asset portfolio modelling
- [ ] Port the legacy bond portfolio logic to a modern ModelIC structure
- [ ] Implement bond cashflows, yield, spread, and valuation logic
- [ ] Add support for bond classes as first-class assets in the portfolio model

#### P1 - ERM / LTM modelling
- [ ] Recreate legacy ERM valuation and redemption logic in ModelIC
- [ ] Implement property / mortgage-type LTM behaviour if still required
- [ ] Add tests that compare ModelIC LTM valuation results with legacy model runs

#### P1 - Liability valuation models
- [ ] Add the legacy liability valuation workflow to ModelIC
- [ ] Confirm best-estimate, SII, and IFRS-style outputs can all be produced
- [ ] Standardise the meaning of "best estimate", "economic value", and "market-consistent" values

#### P1 - Balance sheet engine
- [ ] Build a balance sheet layer similar to the older repos
- [ ] Include assets, liabilities, surplus, and capital outputs
- [ ] Add a clean API for balance sheet valuation and projection

---

### Phase 4: Risk, stress, and management metrics

#### P1 - Matching adjustment / MA logic
- [ ] Confirm the BasicMA work is completed and is suitable for production
- [ ] Add full tests for MA calculations and their interaction with assets and liabilities
- [ ] Validate that MA outputs match legacy model assumptions

#### P1 - SCR / solvency-style metrics
- [ ] Recreate the legacy risk measures needed for regulatory or internal reporting
- [ ] Include mortality stress and interest-rate stress logic
- [ ] Define how ModelIC should expose stress value results

#### P1 - Sensitivity testing
- [ ] Add a scenario engine for varying one or more assumptions
- [ ] Expose a standard way to compare output across stress points
- [ ] Support legacy-style sensitivity charts and summaries

#### P1 - Projection run manager
- [ ] Add a simulation runner similar to the older `RunManager` pattern
- [ ] Support multi-scenario and multi-product valuation runs
- [ ] Save aggregate outputs in a standard, queryable structure

---

### Phase 5: Data input and output compatibility

#### P1 - Data loaders and file compatibility
- [ ] Make ModelIC able to read the same data shapes as legacy repos
- [ ] Support CSV formats from legacy inputs
- [ ] Add a compatibility layer for older parameter files and policy data

#### P1 - Results export
- [ ] Add export of valuation results to CSV / parquet / Excel-style output if needed
- [ ] Provide a standard results schema so old dashboards can still consume the outputs

#### P1 - Reporting and dashboards
- [ ] Port the important dashboard / output views from legacy app code
- [ ] Keep a simple output view for business users and a more analytical view for devs

---

### Phase 6: App/web usability

#### P2 - Legacy web UI parity
- [ ] Decide whether web UI is still required or whether command-line / notebook output is enough
- [ ] If required, port the critical old UI screens into a modern app shell
- [ ] Keep the same user flows for scenario selection and output charts

#### P2 - Simulation UI parity
- [ ] Add interface for running a projected balance sheet or valuation scenario
- [ ] Add ability to view graphs of key outputs
- [ ] Keep the workflow simple enough for non-technical users

---

### Phase 7: Validation and acceptance

#### P1 - Rebuild the legacy regression set
- [ ] For every key legacy product or model, add a benchmark test in ModelIC
- [ ] Compare outputs to legacy results and accept only small numeric differences
- [ ] Record all accepted differences and reasons

#### P1 - Acceptance criteria
ModelIC should be considered feature-complete only when it can:
- price and value all major legacy product types
- handle life, annuity, and endowment products
- price and project asset and liability portfolios
- calculate major balance sheet and risk outputs
- support sensitivity and scenario analysis
- run with legacy file inputs or a compatibility layer
- produce business-grade outputs with tests and documentation

## 6. Likely missing feature areas

These are the areas most likely to need work before ModelIC is truly a full replacement:
- with-profits and bonus features
- bond and ERM portfolio modelling
- larger balance-sheet engine
- risk margin / solvency metrics
- stress-run orchestration
- dashboard/reporting layer
- compatibility with legacy input volumes and CSV structures

## 7. Recommended order of work

1. Mortality, curves, products, cashflows
2. Liability and balance sheet engine
3. Bond / asset / ERM portfolio logic
4. Matching adjustment and stress metrics
5. Web / output reporting layer
6. Regression and final feature parity sign-off

## 8. Suggested practical rule

Do not add a feature to ModelIC unless it has:
- a test
- a legacy benchmark or reason for the design
- a clear API
- a documented output meaning

That keeps the modern repo from becoming another legacy monolith.

## 9. Final decision

The right path is:
- ModelIC as the main repo
- legacy repos as the source of requirements and benchmark outputs
- port missing legacy functionality in structured chunks
- preserve the better design of ModelIC rather than copying the old monolithic architecture wholesale

This is the best route to reach a clean, maintainable actuarial engine without losing the business functionality that already exists in the earlier models.

