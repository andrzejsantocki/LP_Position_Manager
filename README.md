# Liquidity Pool Position Manager 📈

Welcome to the Liquidity Pool Position Manager! This Python application is designed to help you track, manage, and analyze liquidity pool positions. Whether you’re interested in monitoring APY, tracking fees, or managing rebalancing actions, this tool brings clarity to your crypto investments.

---

## Features 🌟

- **Position Management:** Create, view, and modify your liquidity pool positions across different crypto pairs.
- **APY Calculation:** Calculate the Annual Percentage Yield (APY) based on fees, bonuses, and the duration of your investments.
- **Fee Tracking:** Record and view fees associated with each position to better understand your earnings.
- **Rebalancing Management:** Log rebalancing actions to keep your pool balanced and on track.
- **Data Persistence:** All data is stored using `pickle`, allowing you to save your progress between sessions.

---

## How It Works 🛠️

The application runs through a terminal-based interface that guides you in managing various aspects of your liquidity pool investments. The main menu options give you the flexibility to monitor and update your portfolio with ease.

### Main Menu Options

1. **View Positions**: Displays your current liquidity positions, including details on fees and bonus entries.
2. **Calculate Overall APY**: Provides a summary of your APY across all positions.
3. **Modify Position**: Update quantities, fees, or bonuses for any existing position.
4. **Book a Fee**: Record specific fees associated with each liquidity pair.
5. **Book Rebalancing**: Log rebalancing actions to keep positions balanced and aligned with your strategy.

---

## Sample Screenshots 📸

Here are some examples of how the interface looks in action:

| Main Menu | Position Details |
|-----------|------------------|
| ![Main Menu Screenshot](path/to/main_menu_screenshot.png) | ![Position Details Screenshot](path/to/position_details_screenshot.png) |

---

## Installation 📥

Follow these steps to set up the application:

1. **Clone the Repository**:
   ```bash
2. **Install Required Packages**
   ```pip install matplotlib
3. **Run the Application**
   ```python main.py

## Usage 🚀

Once you start the application, you’ll be prompted to select options from the main menu. Here’s a quick overview of what each option does:

- **View Positions**: Lists all liquidity pool positions with associated details.
- **Calculate Overall APY**: Summarizes APY across positions based on fees, duration, and bonuses.
- **Modify Position**: Allows you to make adjustments to any existing position.
- **Book a Fee**: Record additional fees for specific pairs, which impact overall APY.
- **Book Rebalancing**: Log and track rebalancing actions to keep your positions optimized.

Data is saved in `liquidity_positions.pkl` and `balance_movements.pkl`, so your data persists between sessions.

---

## Data Persistence 🗂️

All position and rebalancing data is stored in `.pkl` files, making it easy to resume from where you left off. These files ensure that your progress is saved and accessible whenever you restart the application.

---

## Future Improvements 🔮

Here are some potential future updates to enhance the functionality of the app:

- **Automated APY Charts**: Visualize APY trends over time for each pair.
- **Historical Analysis**: Review how past rebalancing actions have impacted overall performance.
- **Data Export**: Export positions and performance data to CSV or Excel for further analysis and reporting.

---

## License 📄

This project is licensed under the MIT License. See the [LICENSE]
