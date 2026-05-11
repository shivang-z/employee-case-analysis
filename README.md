# Employee Case Analysis Explorer

A Streamlit analytics app for exploring employee performance across `TestName` / `PayorName` combinations and creating leadership-level workforce planning insights.

The app helps answer:

1. **Employee Deep-Dive**: What combinations is an individual employee strongest on?
2. **Best Employees by Test / Payor**: For a selected work type, which employees are the best fit?
3. **Opportunity Finder**: Who appears strong but underutilized?
4. **Coverage Risk**: Which combinations depend on too few strong employees?

---

## Project Overview

This project uses employee case-processing output files generated from a Snowflake-based analysis pipeline.

The original analysis pulls visit-level data, cleans and aggregates it, and creates historical performance and recommendation outputs. The Streamlit app uses those outputs to provide an interactive decision-support interface.

The app currently uses two main CSV files:

- `historical_combo.csv`
- `recency_recommendations.csv`

---

## Folder Structure

Recommended structure:

```text
employee_case_app/
│
├── app.py
├── config.py
├── data_loader.py
├── analytics.py
├── ui_helpers.py
├── requirements.txt
├── README.md
│
└── employee_case_analysis_outputs/
    ├── historical_combo.csv
    └── recency_recommendations.csv
```

---

## Required Files

### `historical_combo.csv`

Used for employee-level historical analytics.

Important columns:

| Column | Description |
|---|---|
| `matched_employee_name` | Employee name |
| `matched_email` | Employee email |
| `matched_shore` | Employee shore/location group |
| `testname` | Test name |
| `payorname` | Payor name |
| `active_days` | Number of days employee worked the combination |
| `historical_total_unique_cases` | Total unique cases handled historically |
| `historical_total_touches` | Total touches/cases worked |
| `avg_daily_unique_cases` | Average daily unique cases |
| `median_daily_unique_cases` | Median daily unique cases |
| `max_daily_unique_cases` | Peak daily unique case count |
| `std_daily_unique_cases` | Standard deviation of daily unique cases |
| `consistency_cv_cases` | Coefficient of variation for consistency |
| `avg_touches_per_case` | Average touches per unique case |

### `recency_recommendations.csv`

Used for recommendation-based views, Opportunity Finder, and Coverage Risk.

Important columns:

| Column | Description |
|---|---|
| `matched_employee_name` | Employee name |
| `matched_email` | Employee email |
| `matched_shore` | Employee shore/location group |
| `testname` | Test name |
| `payorname` | Payor name |
| `observed_days` | Number of days employee worked the combination |
| `recency_weighted_avg_cases` | Recent weighted average daily cases |
| `avg_daily_unique_cases` | Historical average daily unique cases |
| `max_daily_unique_cases` | Peak daily unique cases |
| `consistency_score` | Stability score |
| `recency_recommendation_score` | Final recommendation score |
| `employee_recency_rank_for_combo` | Employee-level rank of combinations |

---

## Key Features

### 1. Employee Deep-Dive

Select an employee and view their historical performance across `TestName` / `PayorName` combinations.

This section shows:

- Total historical unique cases
- Total touches
- Best average daily cases
- Best peak daily cases
- Number of combinations worked
- Historical performance by combination
- Recommended combinations for the selected employee

Business question answered:

> What is this employee best suited for?

---

### 2. Best Employees by Test / Payor

Select a specific `TestName` and `PayorName` combination and view the best recommended employees for that work type.

This section shows:

- Recommended employees
- Recommendation score
- Observed days
- Confidence level
- Recent weighted average cases
- Average daily unique cases
- Max daily unique cases
- Recommendation reason

Business question answered:

> Who should be assigned to this type of work?

---

### 3. Opportunity Finder

Opportunity Finder identifies employees who have a strong recommendation score for a combination but relatively low observed usage.

Core idea:

```text
High recommendation score + low observed days = hidden opportunity
```

This helps identify employees who may be capable of handling more work for a combination but are currently underutilized.

Business use cases:

- Identify hidden strengths
- Expand employee utilization
- Find employees who could take on more work
- Support staffing optimization

---

### 4. Coverage Risk

Coverage Risk identifies `TestName` / `PayorName` combinations that may depend on too few strong employees.

Risk levels:

| Risk Level | Logic | Meaning |
|---|---|---|
| Critical | 0 or 1 strong employee | High dependency risk |
| Medium | 2 to 3 strong employees | Some backup exists, but coverage is limited |
| Low | More than 3 strong employees | Healthy coverage |

Business question answered:

> Which work types are at risk because too few employees are strong candidates?

---

## Recommendation Logic

The recommendation model is designed to be explainable.

It combines signals such as:

| Signal | Meaning |
|---|---|
| Recent productivity | How well the employee has performed recently |
| Average productivity | Typical historical output |
| Peak performance | Best demonstrated daily capacity |
| Evidence | How many observed days support the recommendation |
| Consistency | How stable the employee's performance is |

The goal is to recommend employee-combination fits that are high-performing, reliable, and easy to explain.

---

## Opportunity Finder Logic

Opportunity Finder works at the employee + combination level.

Each row represents:

```text
employee + testname + payorname
```

The feature identifies rows where:

```text
recommendation score is high
AND
observed days are low
```

### Main calculations

High Score Flag:

```text
high_score_flag = recommendation_score >= 75th percentile of recommendation scores
```

Low Usage Flag:

```text
low_usage_flag = observed_days <= 35th percentile of observed days
```

Opportunity Flag:

```text
opportunity_flag = high_score_flag AND low_usage_flag
```

Usage Gap Score:

```text
usage_gap_score = 1 - observed_days / max_observed_days
```

Opportunity Score:

```text
opportunity_score = recommendation_score * usage_gap_score
```

### Opportunity Labels

| Label | Meaning |
|---|---|
| High Opportunity | High score and low usage |
| Strong but already used | High score but not low usage |
| Low exposure | Low usage but not high score |
| Normal | No special flag |

---

## Coverage Risk Logic

Coverage Risk works at the `TestName` / `PayorName` combination level.

Each output row represents:

```text
testname + payorname
```

The goal is to count how many strong employees exist for each combination.

### Combo-Specific Strong Candidate Logic

Employees are compared only against other employees for the same `TestName` / `PayorName`.

```text
combo_score_percentile =
    percentile rank of recommendation score within the same testname/payorname
```

Then:

```text
strong_candidate_flag = combo_score_percentile >= 0.75
```

This means an employee is considered strong if they are in the top 25% for that specific combination.

This is better than using a global cutoff because different combinations can have very different difficulty and volume patterns.

### Coverage Metrics

| Metric | Meaning |
|---|---|
| `total_employees` | Number of employees with data for the combination |
| `strong_employees` | Number of employees in the top 25% for that combination |
| `avg_score` | Average recommendation score for the combination |
| `max_score` | Best recommendation score for the combination |
| `median_score` | Median recommendation score for the combination |
| `strong_employee_pct` | Percentage of employees considered strong |
| `coverage_risk` | Risk category based on strong employee count |

---

## Installation

Create and activate a virtual environment.

Windows:

```bash
python -m venv venv
venv\Scripts\activate
```

macOS/Linux:

```bash
python -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Example `requirements.txt`:

```text
streamlit
pandas
numpy
```

---

## Running the App

From the project folder, run:

```bash
streamlit run app.py
```

The app should open at:

```text
http://localhost:8501
```

---

## How to Use

1. Place the required CSV files inside `employee_case_analysis_outputs/`, or upload them from the sidebar.
2. Optionally apply the shore/location filter.
3. Explore the tabs:
   - `Employee Deep-Dive`
   - `Best Employees by Test / Payor`
   - `Opportunity Finder`
   - `Coverage Risk`

---

## Business Value

The app helps leadership and operations teams:

- Identify employee strengths
- Recommend employees for specific work types
- Find underutilized employees
- Detect coverage risk
- Support cross-training decisions
- Reduce single-person dependency
- Improve workforce planning

---

## Future Enhancements

Potential high-impact additions:

### 1. Primary / Backup / Training Candidate View

Classify employees for each combination as:

- Primary candidate
- Backup candidate
- Training candidate

### 2. What-If Weight Simulator

Allow users to adjust scoring weights interactively:

- Productivity weight
- Peak performance weight
- Evidence weight
- Consistency weight

### 3. Quality-Aware Recommendations

Add quality metrics if available:

- Error rate
- Rework rate
- SLA adherence
- First-pass success rate

### 4. Backtesting

Validate whether high-ranked recommendations actually perform well in a later time period.

### 5. Machine Learning Ranking Model

Use historical data to train a supervised ranking model that predicts the best employee-combination fit.

Possible approaches:

- Learning-to-rank model
- Gradient boosting model
- Classification or regression model for future productivity
- Clustering employees into specialist/generalist profiles

---

## Notes and Assumptions

- `observed_days` is used as a proxy for employee exposure or usage.
- Recommendation scores are assumed to be precomputed in the CSV.
- Coverage Risk uses combo-specific percentiles, not a global score cutoff.
- Opportunity Finder thresholds are configurable and can be tuned based on business needs.
- This app is intended as a decision-support tool, not an automated assignment system.

---

## Suggested Meeting Explanation

> This app takes the recommendation output and turns it into a decision-support interface. It allows users to inspect individual employee performance, identify the best employees for a selected TestName / PayorName, find underutilized strengths through Opportunity Finder, and detect operational dependency risk using Coverage Risk. The logic is explainable and modular, so we can easily extend it with quality metrics, what-if scoring, and machine learning validation later.

---

## Author

Created as part of the Employee Case Analysis and Recommendation System project.
