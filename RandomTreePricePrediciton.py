import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, ParameterGrid
from sklearn.metrics import classification_report, precision_score
from sklearn.preprocessing import StandardScaler
from imblearn.over_sampling import SMOTE
from rich.console import Console
from rich.table import Table
import os

# Set environment variable to avoid CPU warnings
os.environ["LOKY_MAX_CPU_COUNT"] = "6"

# File path for CSV
file_path = "test.csv"

# User input for minimum growth threshold and lookback period
min_growth_rate = float(input("Enter the minimum growth rate to consider (%): "))
lookback_period = int(input("Enter the lookback period (days): "))

console = Console()


def preprocess_data(file_path):
    """Load and preprocess the CSV data."""
    df = pd.read_csv(file_path, delimiter=";")
    df.columns = df.columns.str.strip()
    df = df.drop(columns=["Unnamed: 5", "Unnamed: 6"], errors="ignore")

    # Convert columns to appropriate types
    df["Data"] = pd.to_datetime(df["Data"], format="%Y-%m-%d")
    df[["Open", "High", "Low", "Close"]] = (
        df[["Open", "High", "Low", "Close"]]
        .replace(",", ".", regex=True)
        .astype(float)
    )

    # Feature engineering
    df["Daily_Change"] = (df["Close"] - df["Open"]) / df["Open"] * 100
    df["Growth_Rate"] = df["Close"].pct_change() * 100
    df["Moving_Avg"] = df["Close"].rolling(window=20).mean()
    df["Volatility"] = df["Close"].rolling(window=20).std()
    df["Upper_Band"] = df["Moving_Avg"] + (df["Volatility"] * 2)
    df["Lower_Band"] = df["Moving_Avg"] - (df["Volatility"] * 2)

    # Drop rows with NaN values
    df.dropna(inplace=True)
    return df


def label_rapid_growth(df, threshold, lookback):
    """Label periods of rapid growth based on relative cumulative growth and lookback period."""
    df = df.reset_index(drop=True)
    df["in_rapid_growth"] = 0
    df["Cumulative_Growth"] = 0.0

    in_growth = False
    local_max = -np.inf
    growth_start_idx = None

    for i in range(len(df)):
        if i >= lookback:
            past_price = df.loc[i - lookback, "Close"]
            current_price = df.loc[i, "Close"]

            # Check if current price is higher or equal to the price 'lookback' days ago
            if current_price >= past_price:
                # Calculate cumulative growth relative to the lookback price
                cumulative_growth = (current_price - past_price) / past_price * 100
                df.loc[i, "Cumulative_Growth"] = cumulative_growth

                if cumulative_growth >= threshold:
                    if not in_growth:
                        in_growth = True
                        growth_start_idx = i
                    df.loc[growth_start_idx:i, "in_rapid_growth"] = 1

            # Reset growth if local max is reached
            local_max = max(local_max, current_price)
            if in_growth and current_price < local_max:
                in_growth = False

    return df


def train_models_with_smote(df):
    """Train models with SMOTE for oversampling the minority class."""
    features = ["Open", "High", "Low", "Close", "Daily_Change", "Moving_Avg", "Growth_Rate", "Volatility"]
    X = df[features]
    y = df["in_rapid_growth"]

    # Standardize features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Apply SMOTE to balance the dataset
    smote = SMOTE(random_state=42)
    X_resampled, y_resampled = smote.fit_resample(X_scaled, y)

    # Train-test split
    X_train, X_test, y_train, y_test = train_test_split(X_resampled, y_resampled, test_size=0.3, random_state=42)

    # Hyperparameter grid
    param_grid = {
        "n_estimators": [100, 200],
        "max_depth": [5, 10, None],
        "min_samples_split": [2, 5],
    }

    # Train Random Forest with hyperparameter optimization
    best_model = None
    best_precision = 0

    for params in ParameterGrid(param_grid):
        model = RandomForestClassifier(random_state=42, **params)
        model.fit(X_train, y_train)
        precision = precision_score(y_test, model.predict(X_test))
        if precision > best_precision:
            best_precision = precision
            best_model = model

    # Evaluate the final model
    console.print("\n[INFO] Evaluating Growth Model:", style="bold cyan")
    y_pred = best_model.predict(X_test)
    console.print(classification_report(y_test, y_pred))

    return best_model, scaler


def calculate_statistics(trade_log, balance_history, df):
    """Calculate additional statistics."""
    # Sharpe Ratio
    daily_returns = pd.Series(balance_history).pct_change().dropna()
    sharpe_ratio = (daily_returns.mean() - 0.04 / 252) / daily_returns.std() * np.sqrt(252)

    # Days below average price
    mean_price = df["Close"].mean()
    days_below_avg = (df["Close"] < mean_price).sum()

    # Total trades
    total_trades = len(trade_log)

    # Trades per month
    months = (df["Data"].iloc[-1] - df["Data"].iloc[0]).days / 30
    trades_per_month = total_trades / months if months > 0 else 0

    # Volatility
    volatility = daily_returns.std()

    return sharpe_ratio, days_below_avg, total_trades, trades_per_month, volatility


def display_results(final_balance, max_drawdown, mean_drawdown, sharpe_ratio, days_below_avg, total_trades,
                    trades_per_month, volatility, trade_log):
    """Display statistics in a table."""
    table = Table(title="Trading Strategy Statistics")
    table.add_column("Metric", justify="left")
    table.add_column("Value", justify="right")

    table.add_row("Final Balance ($)", f"{final_balance:.2f}")
    table.add_row("Max Drawdown (%)", f"{max_drawdown * 100:.2f}")
    table.add_row("Mean Drawdown (%)", f"{mean_drawdown * 100:.2f}")
    table.add_row("Sharpe Ratio", f"{sharpe_ratio:.2f}")
    table.add_row("Days Below Average Price", f"{days_below_avg}")
    table.add_row("Total Trades", f"{total_trades}")
    table.add_row("Trades per Month", f"{trades_per_month:.2f}")
    table.add_row("Volatility (%)", f"{volatility * 100:.2f}")

    console.print(table)

    console.print("\n[INFO] Trade Log:", style="bold cyan")
    for log in trade_log:
        console.print(
            f"{log['Action']} at {log['Price']:.4f} on {log['Date']} - Traded: ${log['Traded_Value']:.2f} - Balance: ${log['Remaining_Balance']:.2f}")


def plot_high_growth_and_balance(df, trade_log, balance_history):
    """Plot high-growth areas, trade points, and portfolio balance."""
    fig, axs = plt.subplots(2, 1, figsize=(14, 10), gridspec_kw={'height_ratios': [2, 1]})

    # Plot price movement and trades
    axs[0].plot(df["Data"], df["Close"], label="Price", color="blue", alpha=0.5)
    axs[0].fill_between(
        df["Data"],
        df["Close"],
        where=df["in_rapid_growth"] == 1,
        color="yellow",
        alpha=0.3,
        label="High Growth Area",
    )

    for log in trade_log:
        if log["Action"] == "BUY":
            axs[0].scatter(log["Date"], log["Price"], color="green", label="Buy", zorder=5)
        elif log["Action"] == "SELL":
            axs[0].scatter(log["Date"], log["Price"], color="red", label="Sell", zorder=5)

    axs[0].set_title("Price Movement and Trades", fontsize=16)
    axs[0].set_ylabel("Price", fontsize=12)
    axs[0].grid(alpha=0.3)

    # Plot portfolio balance
    axs[1].plot(df["Data"], balance_history, label="Portfolio Balance", color="purple")
    axs[1].set_title("Portfolio Balance Over Time", fontsize=16)
    axs[1].set_xlabel("Date", fontsize=12)
    axs[1].set_ylabel("Balance", fontsize=12)
    axs[1].grid(alpha=0.3)

    plt.tight_layout()
    plt.show()


def main():
    """Main function to process, label, and plot the data."""
    console.print("[INFO] Preprocessing data...", style="bold green")
    df = preprocess_data(file_path)

    console.print("[INFO] Labeling rapid growth periods...", style="bold green")
    df = label_rapid_growth(df, min_growth_rate, lookback_period)

    console.print("[INFO] Training models with SMOTE...", style="bold green")
    model, scaler = train_models_with_smote(df)

    console.print("[INFO] Simulating trading...", style="bold green")
    features = ["Open", "High", "Low", "Close", "Daily_Change", "Moving_Avg", "Growth_Rate", "Volatility"]
    X_scaled = scaler.transform(df[features])
    df["Growth_Prediction"] = model.predict(X_scaled)

    balance = 1000
    holdings = 0
    balance_history = []
    trade_log = []

    for i, row in df.iterrows():
        if row["Growth_Prediction"] == 1 and holdings == 0:
            amount_traded = balance
            holdings = balance / row["Close"]
            balance = 0
            trade_log.append({
                "Action": "BUY",
                "Price": row["Close"],
                "Date": row["Data"],
                "Traded_Value": amount_traded,
                "Remaining_Balance": balance,
            })
        elif holdings > 0 and row["Growth_Prediction"] == 0:
            amount_traded = holdings * row["Close"]
            balance = amount_traded
            trade_log.append({
                "Action": "SELL",
                "Price": row["Close"],
                "Date": row["Data"],
                "Traded_Value": amount_traded,
                "Remaining_Balance": balance,
            })
            holdings = 0
        balance_history.append(balance + (holdings * row["Close"]))

    final_balance = balance + (holdings * df.iloc[-1]["Close"] if holdings > 0 else 0)
    balance_history = pd.Series(balance_history)
    max_drawdown = ((balance_history - balance_history.cummax()) / balance_history.cummax()).min()
    mean_drawdown = ((balance_history - balance_history.cummax()) / balance_history.cummax()).mean()

    sharpe_ratio, days_below_avg, total_trades, trades_per_month, volatility = calculate_statistics(trade_log,
                                                                                                    balance_history, df)

    console.print("[INFO] Displaying results...", style="bold green")
    display_results(final_balance, max_drawdown, mean_drawdown, sharpe_ratio, days_below_avg, total_trades,
                    trades_per_month, volatility, trade_log)

    console.print("[INFO] Plotting high-growth areas, trades, and balance...", style="bold green")
    plot_high_growth_and_balance(df, trade_log, balance_history)


if __name__ == "__main__":
    main()
