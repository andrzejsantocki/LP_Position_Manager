import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# File path for CSV
file_path = "test.csv"

# User input for combined threshold (percentage) and lookback period (days)
growth_threshold = float(input("Enter the relative growth threshold (%): "))
lookback_period = int(input("Enter the lookback period (days): "))


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

    return df


def label_rapid_growth(df, threshold, lookback):
    """Label rapid growth areas based on relative cumulative growth and local maxima."""
    df["in_rapid_growth"] = 0
    df["Cumulative_Growth"] = 0.0

    in_growth = False
    local_max = -np.inf
    growth_start_idx = None

    for i in range(len(df)):
        # Check if within lookback period
        if i >= lookback:
            past_price = df.loc[i - lookback, "Close"]
            current_price = df.loc[i, "Close"]

            # Check if current price is higher or equal to the price 'lookback' days ago
            if current_price >= past_price:
                # Add to cumulative growth
                if not in_growth:
                    in_growth = True
                    growth_start_idx = i
                    df.loc[growth_start_idx:i, "in_rapid_growth"] = 1
                else:
                    df.loc[growth_start_idx:i, "in_rapid_growth"] = 1

                # Update local max
                local_max = max(local_max, current_price)
                cumulative_growth = (current_price - past_price) / past_price * 100
                df.loc[i, "Cumulative_Growth"] = cumulative_growth

        # Stop labeling if local max is reached
        if in_growth and df.loc[i, "Close"] < local_max:
            in_growth = False

    # Combine overlapping periods
    df["in_rapid_growth"] = df["in_rapid_growth"].rolling(window=lookback, min_periods=1).max().astype(int)

    return df


def plot_high_growth_areas(df):
    """Plot the high-growth areas with cumulative growth exceeding the threshold."""
    plt.figure(figsize=(14, 7))
    plt.plot(df["Data"], df["Close"], label="Price", color="blue", alpha=0.5)

    # Highlight rapid growth areas
    rapid_growth = df[df["in_rapid_growth"] == 1]
    plt.fill_between(
        df["Data"],
        df["Close"],
        where=df["in_rapid_growth"] == 1,
        color="yellow",
        alpha=0.3,
        label="High Growth Area",
    )

    plt.title("Price and High Growth Areas", fontsize=16)
    plt.xlabel("Date", fontsize=12)
    plt.ylabel("Price", fontsize=12)
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.show()


def main():
    """Main function to process, label, and plot the data."""
    print("[INFO] Preprocessing data...")
    df = preprocess_data(file_path)

    print("[INFO] Labeling rapid growth periods...")
    df = label_rapid_growth(df, growth_threshold, lookback_period)

    print("[INFO] Plotting high-growth areas...")
    plot_high_growth_areas(df)


if __name__ == "__main__":
    main()
