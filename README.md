# TyrusBurton-Python-Finance-Projects
Python projects tracking my journey into financial analysis and data.

---

## Project 1: Cumulative Returns Analysis | ASML, MSFT, VOO

**Libraries:** yfinance, pandas, pandas_datareader, datetime, numpy, matplotlib

**Process:** Used yfinance to pull 5 years of historical data via the Yahoo Finance API, retrieving open, high, low, close, and volume for each ticker. Isolated the adjusted closing price, calculated daily log returns by dividing each day's price by the prior day's and taking the natural log, then applied cumsum to generate cumulative log returns across the full window. Plotted all three securities on a single time-series chart for direct comparison.

**Result:** ASML showed the highest volatility, dropping nearly 50% through 2023 before rebounding ~70% cumulative. MSFT finished around 40%, VOO around 50%.

![Cumulative Returns](cumulative_returns.png)


## Project 2: Credit Risk Analysis | Loan Default Prediction

**Libraries:** pandas, numpy, matplotlib, scikit-learn

**Dataset:** 32,581 real loan applications from Kaggle (nanditapore/credit-risk-analysis) with 12 features including borrower age, income, employment length, loan amount, interest rate, loan grade, and credit history.

**Process:** Loaded and explored the dataset via EDA — checked shape, summary statistics, missing values, and data types. Identified 895 missing values in person_emp_length and 3,116 in loan_int_rate, filled both with column medians to preserve data. Encoded categorical variables (home ownership, loan intent, loan grade, prior default history) using pd.get_dummies, expanding the feature set from 12 to 27 columns. Split data 80/20 into training and testing sets. Scaled features using StandardScaler to normalize columns operating on vastly different scales. Trained a Logistic Regression model using the saga solver.

**Key Decision:** Initial model achieved 86% accuracy but only 54% recall on actual defaulters — meaning it missed 46% of loans that went bad. Identified this as a class imbalance problem (5,072 non-defaulters vs 1,445 defaulters in the test set). Applied class_weight='balanced' to penalize missed defaults more heavily.

**Result:** Recall on defaulters improved from 54% to 78% with an AUC-ROC of 0.87, meaning the model correctly identifies 78 out of every 100 actual defaulters in turn creating a significantly safer model for real-world credit risk application.
