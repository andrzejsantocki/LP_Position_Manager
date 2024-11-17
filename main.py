import pickle
import os
import time
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import requests
from datetime import datetime
import sys
import urllib
from rich import print as rich_print
from rich.console import Console
import builtins

# Paths to store the positions and rebalancing entries
DATA_FILE = 'liquidity_positions_db.pkl'
REBALANCE_FILE = 'balance_movements_db.pkl'
LP_NOTIONALS_FILE = 'lp_notionals_db.pkl'  # New file to store LP notionals


# Create a Console instance
console = Console()

# List of popular colors (add more if needed)
COLOR_LIST = [
    "red", "green", "blue", "yellow", "cyan", "magenta", "white", "black",
    "bright_red", "bright_green", "bright_blue", "bright_yellow",
    "bright_cyan", "bright_magenta", "bright_white"
]


def rerunnable(func):
    def wrapper(*args, **kwargs):
        wrapper.last_args = args
        wrapper.last_kwargs = kwargs
        while True:
            try:
                return func(*args, **kwargs)
            except ValueError as e:
                message = str(e)
                if message == "Restart Entry":
                    continue  # Rerun the function
                elif message == "Quit Entry":
                    break  # Exit the loop and end the function
                else:
                    print(f"An error occurred: {message}")
                    break  # Optionally, you can re-raise the exception here

    def rerun_if(condition):
        """Reruns the function only if the condition is True"""
        if condition:
            return wrapper(*wrapper.last_args, **wrapper.last_kwargs)

    wrapper.rerun_if = rerun_if
    return wrapper




def print(*args, color=None, sep=" ", end="\n"):
    # Join arguments with separator
    text = sep.join(str(arg) for arg in args)

    # If a color is specified and valid, use rich's Console for colorized output
    if color in COLOR_LIST:
        console.print(f"[{color}]{text}[/{color}]", end=end)
    else:
        # Use the built-in print function for non-colorized text
        builtins.print(text, sep=sep, end=end)


# overwrite input function
def input(prompt, color=None):
    if color in COLOR_LIST:
        # Print the prompt with the specified color
        rich_print(f"[{color}]{prompt}[/{color}]", end="")
    else:
        # Print the prompt without color
        rich_print(prompt, end="")

    # Return the user input captured by the built-in input()
    return __builtins__.input()


def get_input(prompt, default_value,colour = "white"):
    console.print(f"[{colour}]{prompt}[/{colour}]",end = "")
    user_input = input("").strip()

    # If input is empty, return the default value
    if user_input == '':
        return default_value

    if user_input == '..':
        print('Restarting entry \n')
        raise ValueError("Restart Entry")

    if user_input == 'q':
        print('Quit entry \n')
        raise ValueError("Quit Entry")

    # Attempt to handle numeric values with commas or dots
    try:
        # Replace commas with dots and try converting to float
        numeric_value = float(user_input.replace(",", "."))

        # Check if the float is a whole number
        if numeric_value.is_integer():
            return str(int(numeric_value))  # Return as an integer-like string
        return str(numeric_value)  # Return as a string with dot as decimal separator for non-whole numbers
    except ValueError:
        # If conversion fails, return the input as it is (non-numeric text)
        return user_input or default_value  # if user_input is null return default_value


def get_coin_id(coin_name, colour = "blue"):
    url = 'https://api.coingecko.com/api/v3/search'
    headers = {
        'User-Agent': 'Mozilla/5.0'
    }
    params = {
        'query': coin_name
    }
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        data = response.json()
        coins = data.get('coins', [])
        if coins:
            print(f"\nCoins found for '{coin_name}':")
            for idx, coin in enumerate(coins):
                print(f"{idx + 1}: {coin['name']} (ID: {coin['id']}, Symbol: {coin['symbol']})")
            console.print(f"[{colour}]{"Enter the number of the coin you want to use: "}[/{colour}]", end="")
            choice = input("").strip()

            # print(choice, "<-choice")
            # print(len(coins), len(coins))
            try:
                choice = int(choice) - 1
                if 0 <= choice < len(coins):
                    return coins[choice]['id']
                else:
                    print("Invalid choice.")
                    return None
            except ValueError:
                print("Invalid input.")
                return None
        else:
            print(f"No coins found for '{coin_name}'.")
            return None
    else:
        print(f"Error fetching coin list: {response.status_code}")
        return None


@rerunnable
def fetch_coin_prices(coin_id, days):
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
    params = {
        'vs_currency': 'usd',
        'days': str(days)
    }
    headers = {
        'User-Agent': 'Mozilla/5.0'
    }
    response = requests.get(url, params=params, headers=headers)
    print(f"Requesting URL: {response.url}")  # Debugging line
    if response.status_code == 200:
        data = response.json()
        prices = data.get('prices', [])
        if prices:
            df = pd.DataFrame(prices, columns=['timestamp', 'price'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
            df.set_index('timestamp', inplace=True)
            return df
        else:
            print(f"No price data available for {coin_id}.")
            return None
    else:
        print(f"Error fetching prices for {coin_id}: {response.status_code}")
        print(f"Response content: {response.text}")
        return None


def get_latest_price(coin_id):
    """
    Fetches the current price for a given CoinGecko coin ID.

    Args:
        coin_id (str): The unique CoinGecko ID of the cryptocurrency.

    Returns:
        float: The latest available price in USD, or None if unavailable.
    """
    if not isinstance(coin_id, str):
        print(f"Invalid type for coin_id: {type(coin_id)}, value: {coin_id}")
        return None

    coin_id_encoded = urllib.parse.quote(coin_id)

    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        'ids': coin_id_encoded,
        'vs_currencies': 'usd'
    }
    headers = {
        'User-Agent': 'Mozilla/5.0'
    }

    print(f"Fetching price for coin ID: {coin_id}")
    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        data = response.json()
        # print(f"Response data: {data}")
        price = data.get(coin_id, {}).get('usd')
        if price is not None:
            return price
        else:
            print(f"No price data available for {coin_id}. Please check if the coin ID is correct.")
            return None
    else:
        print(f"Error fetching price for {coin_id}: {response.status_code} - {response.text}")
        print('Delaying 10 seconds before attempting to fetch price again...')
        time.sleep(10)
        return get_latest_price(coin_id)

    return None


# Helper functions for positions data
def load_positions():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'rb') as f:
            return pickle.load(f)
    return []


def save_positions(positions):
    with open(DATA_FILE, 'wb') as f:
        pickle.dump(positions, f)


# Helper functions for balance movements data
def load_balance_movements():
    if os.path.exists(REBALANCE_FILE):
        with open(REBALANCE_FILE, 'rb') as f:
            return pickle.load(f)
    return []


def save_balance_movements(balance_movements):
    with open(REBALANCE_FILE, 'wb') as f:
        pickle.dump(balance_movements, f)


# Helper functions for LP notionals data
def load_lp_notionals():
    if os.path.exists(LP_NOTIONALS_FILE):
        with open(LP_NOTIONALS_FILE, 'rb') as f:
            return pickle.load(f)
    return []


def save_lp_notionals(lp_notionals):
    with open(LP_NOTIONALS_FILE, 'wb') as f:
        pickle.dump(lp_notionals, f)


# Helper function to handle default inputs (auto-d

# Function to book a new fee
@rerunnable
def book_fee():
    positions = load_positions()
    if not positions:
        print("❌ No positions available to book a fee.")
        return

    # Create a map of positions by pair
    position_map = {}
    for position in positions:
        position_map.setdefault(position['pair'], []).append(position)

    # Display available pairs to book a fee
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("💰  SELECT A PAIR TO BOOK A FEE  💰")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    for idx, pair in enumerate(position_map.keys(), 1):
        print(f"{idx}. Pair: {pair}")

    selected_idx = int(get_input("Select a pair by number: ", '0'))
    pairs = list(position_map.keys())
    if selected_idx < 1 or selected_idx > len(pairs):
        print("❌ Invalid selection.")
        return

    selected_pair = pairs[selected_idx - 1]
    fee_amount = float(get_input("Enter the fee amount: ", '0').replace(',', '.'))
    fee_description = get_input("Enter fee description: ", '')

    # Assign current date without time
    fee_date = datetime.now().date()

    # Append the fee to the selected pair's fee list
    for pos in positions:
        if pos['pair'] == selected_pair:
            if 'fees' not in pos:
                pos['fees'] = []
            pos['fees'].append({
                'amount': fee_amount,
                'description': fee_description,
                'date': fee_date
            })
            break

    save_positions(positions)
    print("\n✅ Fee booked successfully.")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


# Function to delete rebalancing entry
@rerunnable
def delete_rebalancing():
    balance_movements = load_balance_movements()
    if not balance_movements:
        print("❌ No rebalancing entries to delete.")
        return

    # Display available pairs
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("🗑️  SELECT A PAIR TO DELETE REBALANCING ENTRY  🗑️")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    pair_set = set([entry['pair'] for entry in balance_movements])
    for idx, pair in enumerate(pair_set, 1):
        print(f"{idx}. {pair}")

    selected_idx = int(get_input("Select a pair by number: ", '0'))
    if selected_idx < 1 or selected_idx > len(pair_set):
        print("❌ Invalid selection.")
        return

    selected_pair = list(pair_set)[selected_idx - 1]

    # Filter rebalancing entries for the selected pair
    filtered_entries = [entry for entry in balance_movements if entry['pair'] == selected_pair]

    # Display rebalancing entries for this pair
    print(f"\n📊  REBALANCING ENTRIES FOR {selected_pair}  📊")
    for idx, entry in enumerate(filtered_entries, 1):
        date_str = entry['date'].strftime("%Y-%m-%d %H:%M")
        min_price = entry.get('min_price', 'N/A')
        max_price = entry.get('max_price', 'N/A')
        print(f"{idx}. Date: {date_str}, Type: {entry['type']}, Min: {min_price}, Max: {max_price}")

    selected_entry_idx = int(get_input("Select an entry to delete: ", '0'))
    if selected_entry_idx < 1 or selected_entry_idx > len(filtered_entries):
        print("❌ Invalid selection.")
        return

    # Remove the selected entry
    balance_movements.remove(filtered_entries[selected_entry_idx - 1])
    save_balance_movements(balance_movements)
    print(f"\n✅ Rebalancing entry deleted successfully.")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


# Function to book a rebalancing
@rerunnable
def book_rebalancing():
    positions = load_positions()
    if not positions:
        print("❌ No positions available to book rebalancing.")
        return

    # Create a map of positions by pair
    position_map = {}
    for position in positions:
        position_map[position['pair']] = position

    # Display available pairs to book rebalancing
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("🔄  SELECT A PAIR TO BOOK REBALANCING  🔄")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    for idx, pair in enumerate(position_map.keys(), 1):
        print(f"{idx}. Pair: {pair}")

    selected_idx = int(get_input("Select a pair by number: ", '0'))
    pairs = list(position_map.keys())
    if selected_idx < 1 or selected_idx > len(pairs):
        print("❌ Invalid selection.")
        return

    selected_pair = pairs[selected_idx - 1]
    action = get_input("Add Rebalancing (a) or Delete Rebalancing (d)? ", "a").lower()

    if action == "a":
        # Get the type of transaction
        print("Select the type of transaction:")
        print("1. Initial")
        print("2. Open LP")
        print("3. Redemption")
        type_dict = {'1': 'initial_balances', '2': 'open_lp_balances', '3': 'redemption_balances'}
        type_choice = get_input("Enter the number corresponding to the type: ", '1')
        transaction_type = type_dict.get(type_choice, 'initial_balances')

        # Proceed to add a new rebalancing
        coin1_name, coin2_name = selected_pair.split('-')

        # Get Metamask balances
        metamask_balance_coin1 = float(get_input(f"Enter remaining Metamask balance for {coin1_name}: ", '0').replace(',', '.'))
        metamask_balance_coin2 = float(get_input(f"Enter remaining Metamask balance for {coin2_name}: ", '0').replace(',', '.'))

        # Get LP balances
        lp_balance_coin1 = float(get_input(f"Enter LP balance for {coin1_name}: ", '0').replace(',', '.'))
        lp_balance_coin2 = float(get_input(f"Enter LP balance for {coin2_name}: ", '0').replace(',', '.'))

        # If it's an "Open LP", ask for min and max prices
        if transaction_type == 'open_lp_balances':
            min_price = float(get_input(f"Enter the minimum price for {selected_pair}: ", '0').replace(',', '.'))
            max_price = float(get_input(f"Enter the maximum price for {selected_pair}: ", '0').replace(',', '.'))
        else:
            min_price = max_price = None

        # Ask for the date and hour of rebalancing (no minutes)
        date_str = get_input("Enter the date of rebalancing (YYYY-MM-DD): ", datetime.now().strftime("%Y-%m-%d"))
        hour_str = get_input("Enter the hour of rebalancing (HH): ", datetime.now().strftime("%H"))[:2]
        rebalance_datetime = datetime.strptime(f"{date_str} {hour_str}", "%Y-%m-%d %H")

        # Add an optional note/description for the rebalancing
        note = get_input("Add an optional note or description for this rebalancing: ", "").strip()

        # Save the entry into balance movements
        balance_movements = load_balance_movements()
        balance_entry = {
            'pair': selected_pair,
            transaction_type: {  # Save under the correct key
                'metamask': {
                    coin1_name: metamask_balance_coin1,
                    coin2_name: metamask_balance_coin2
                },
                'lp': {
                    coin1_name: lp_balance_coin1,
                    coin2_name: lp_balance_coin2
                }
            },
            'type': transaction_type.split('_')[0],
            'min_price': min_price,
            'max_price': max_price,
            'date': rebalance_datetime,
            'note': note  # Save optional note
        }
        balance_movements.append(balance_entry)
        save_balance_movements(balance_movements)

        print("\n✅ Rebalancing booked successfully.")

    elif action == "d":
        # If delete is selected, list available rebalance entries for the selected pair
        balance_movements = load_balance_movements()
        pair_movements = [entry for entry in balance_movements if entry['pair'] == selected_pair]

        if not pair_movements:
            print(f"❌ No rebalancing entries found for pair {selected_pair}.")
            return

        print(f"Available rebalancing entries for {selected_pair}:")
        for idx, entry in enumerate(pair_movements, 1):
            entry_date = entry['date'].strftime("%Y-%m-%d %H:%M:%S")
            entry_type = entry.get('type', 'Unknown')
            print(f"{idx}. Date: {entry_date}, Type: {entry_type}")

        delete_idx = int(get_input("Select an entry to delete by number: ", '0'))
        if delete_idx < 1 or delete_idx > len(pair_movements):
            print("❌ Invalid selection.")
            return

        # Remove the selected entry
        balance_movements.remove(pair_movements[delete_idx - 1])
        save_balance_movements(balance_movements)

        print("\n✅ Rebalancing entry deleted successfully.")






# Function to calculate overall APY
@rerunnable
def calculate_overall_apy():
    positions = load_positions()
    if not positions:
        print("❌ No positions available to calculate overall APY.")
        return

    position_map = {}
    idx_name_map = {}
    for idx, position in enumerate(positions):
        print(f"{idx + 1}. {position['pair']} - Date Added: {position['date_added'].strftime('%Y-%m-%d')}")
        position_map.setdefault(position['pair'], []).append(position)
        idx_name_map[idx] = position['pair']

    selected_position_option_idx = get_input('\nSelect position number: ', '')
    selected_position_option_idx = int(selected_position_option_idx) - 1

    selected_position_option_pair_name = idx_name_map[selected_position_option_idx]
    pos_list = position_map[selected_position_option_pair_name]

    total_weighted_apr = 0
    total_investment_all = 0

    for pair, pos_list in {selected_position_option_pair_name: pos_list}.items():
        print(f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"📊  SUMMARY FOR PAIR: {pair}  📊")
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        # Aggregating values
        total_fee_coin1 = sum(pos['total_fee_coin1'] for pos in pos_list)
        total_fee_coin2 = sum(pos['total_fee_coin2'] for pos in pos_list)
        total_lp_bonus = sum(pos['lp_provider_bonus'] for pos in pos_list)
        total_investor_paid_fees = sum(pos['investor_paid_fees'] for pos in pos_list)
        total_manual_fees = sum(fee['amount'] for pos in pos_list for fee in pos.get('fees', []))

        net_quantity_1 = sum(pos['initial_quantity_1'] for pos in pos_list)
        net_quantity_2 = sum(pos['initial_quantity_2'] for pos in pos_list)

        current_prices = {
            'coin1': get_latest_price(pos_list[0]['coingecko_id_coin1']),
            'coin2': get_latest_price(pos_list[0]['coingecko_id_coin2']),
            'bonus_coin': get_latest_price(pos_list[0]['bonus_coin'])
        }

        total_investment = net_quantity_1 * current_prices['coin1'] + net_quantity_2 * current_prices['coin2']



        earliest_date_added = min(pos['date_added'] for pos in pos_list)
        days_active = (datetime.now() - earliest_date_added).total_seconds() / 86400.0

        # Loan Impact and LTV Calculation
        total_loan = sum(float(pos.get('loan_value', 0)) for pos in pos_list)
        if total_loan > 0:
            loan_coin_id = pos_list[0]['loan_coin_coingecko_id']
            loan_coin_price = get_latest_price(loan_coin_id)

            current_loan_value = float(get_input(f"Current outstanding loan value in {pos_list[0]['loan_coin']}: ", total_loan))
            notional_loan_repayment = current_loan_value * loan_coin_price

            # Collateral Details
            collateral_coin = pos_list[0]['colateral_coin_name']
            collateral_quantity = float(pos_list[0].get('colateral_notional', 0))
            collateral_coin_id = pos_list[0]['colateral_coingecko_id']
            collateral_coin_price = get_latest_price(collateral_coin_id)
            borrowed_value_usd = loan_coin_price * current_loan_value
            collateral_value_usd = collateral_quantity * collateral_coin_price
            print('\n')

            # Calculate LTV
            if collateral_value_usd > 0:
                # print(current_loan_value)
                # print(collateral_value_usd)
                ltv = (borrowed_value_usd / collateral_value_usd) * 100
                print(f"📈 Loan-to-Value (LTV): {ltv:.2f}%")
            else:
                print("❌ Collateral value is zero; cannot calculate LTV.")
                ltv = 0
        else:
            notional_loan_repayment = 0
            ltv = 0
            print("💡 No loan associated with this position.")

        # Total Fees
        total_fees = ((total_fee_coin1 * current_prices['coin1']) +
                      (total_fee_coin2 * current_prices['coin2']) +
                      (total_lp_bonus * current_prices['bonus_coin']) -
                      total_manual_fees - total_investor_paid_fees)

        # Positive Gain
        positive_gain_usdt = total_fees + notional_loan_repayment - total_investment

        # APY Calculation
        if total_investment > 0 and days_active > 0:
            apr = (positive_gain_usdt / total_investment) * (365 / days_active) * 100
        else:
            apr = 0

        # Summary for the pair
        # TVL (Total Value Locked)
        print(f"🧺 TVL (Total Value Locked): ${total_investment:.2f}")
        print(f"✔️ Total Fee (Coin 1): {total_fee_coin1:.6f}")
        print(f"✔️ Total Fee (Coin 2): {total_fee_coin2:.6f}")
        print(f"✔️ LP Provider Bonus: {total_lp_bonus:.6f}")
        print(f"✔️ Total Manual Fees Deducted: {total_manual_fees:.2f}")
        print(f"✔️ Total Investment: ${total_investment:.2f}")
        print(f"✔️ Days Active: {days_active:.2f}")
        print(f"✔️ APY for {pair}: {apr:.2f}%")

        # Weighted APY Calculation
        total_weighted_apr += apr * total_investment
        total_investment_all += total_investment

    # Overall APY
    if total_investment_all > 0:
        overall_apy = total_weighted_apr / total_investment_all
        print(f"\n🌟 Overall APY: {overall_apy:.2f}%")
    else:
        print("❌ No active positions to calculate APY.")


@rerunnable
def calculate_overall_apy_old():
    positions = load_positions()
    notional_outstanding_loan = 0
    if not positions:
        print("❌ No positions available to calculate overall APY.")
        return

    position_map = {}
    idx_name_map = {}
    for idx, position in enumerate(positions):
        print(f"{idx + 1}. {position['pair']} date added: {position['date_added']}")
        position_map.setdefault(position['pair'], []).append(position)
        idx_name_map[idx] = position['pair']

    # Select position by index
    selected_position_option_idx = get_input('\nSelect position number: ', '')
    selected_position_option_idx = int(selected_position_option_idx) - 1  # Convert input to integer

    # Retrieve selected pair name
    selected_position_option_pair_name = idx_name_map[selected_position_option_idx]
    pos_list = position_map[selected_position_option_pair_name]  # Get positions for selected pair

    total_weighted_apr = 0
    total_investment_all = 0

    for pair, pos_list in {selected_position_option_pair_name: pos_list}.items():
        print(f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"📊  SUMMARY FOR PAIR: {pair}  📊")
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        total_loan = sum(float(pos['loan_value']) for pos in pos_list)
        loan_coin_coingecko_id = pos_list[0]['loan_coin_coingecko_id']

        total_fee_coin1 = sum(pos['total_fee_coin1'] for pos in pos_list)
        total_fee_coin2 = sum(pos['total_fee_coin2'] for pos in pos_list)
        total_lp_bonus = sum(pos['lp_provider_bonus'] for pos in pos_list)
        total_investor_paid_fees = sum(pos['investor_paid_fees'] for pos in pos_list)

        # Combine fees from manually booked fees
        total_manual_fees = sum(fee['amount'] for pos in pos_list for fee in pos.get('fees', []))

        current_prices = {
            'coin1': get_latest_price(pos_list[0]['coingecko_id_coin1']),
            'coin2': get_latest_price(pos_list[0]['coingecko_id_coin2']),
            'bonus_coin': get_latest_price(pos_list[0]['bonus_coin'])
        }

        net_quantity_1 = sum(pos['initial_quantity_1'] for pos in pos_list)
        net_quantity_2 = sum(pos['initial_quantity_2'] for pos in pos_list)
        total_investment = net_quantity_1 * current_prices['coin1'] + net_quantity_2 * current_prices['coin2']

        earliest_date_added = min(pos['date_added'] for pos in pos_list)
        time_diff = datetime.now() - earliest_date_added
        days_active = time_diff.days + time_diff.seconds / 86400.0  # Convert seconds to fraction of a day

        if total_loan > 0:
            current_outstanding_loan_value = float(
                get_input(f"Enter provider (ex. Binance) loan value for {pos_list[0]['loan_coin']}: ", total_loan))
            interest_to_repay = current_outstanding_loan_value - total_loan
            loan_coin_current_price_usdt = get_latest_price(pos_list[0]['loan_coin_coingecko_id'])
            notional_outstanding_loan = interest_to_repay * loan_coin_current_price_usdt

            # Include loan and manual fees
            total_fees = ((total_fee_coin1 * current_prices['coin1'] +
                           total_fee_coin2 * current_prices['coin2'] +
                           total_lp_bonus * current_prices['bonus_coin'])
                          - total_investor_paid_fees - total_manual_fees)

            positive_gain_usdt = (total_fee_coin1 * current_prices['coin1']) + \
                                 (total_fee_coin2 * current_prices['coin2']) + \
                                 (total_lp_bonus * current_prices['bonus_coin']) - \
                                 notional_outstanding_loan - total_manual_fees

            if total_investment > 0 and days_active > 0:
                apr = (total_fees / total_investment) * (365 / days_active) * 100
            else:
                apr = 0

        else:
            # Include manual fees in the fee calculation
            total_fees = ((total_fee_coin1 * current_prices['coin1'] +
                           total_fee_coin2 * current_prices['coin2'] +
                           total_lp_bonus * current_prices['bonus_coin'])
                          - total_investor_paid_fees - total_manual_fees)

            positive_gain_usdt = (total_fee_coin1 * current_prices['coin1']) + \
                                 (total_fee_coin2 * current_prices['coin2']) + \
                                 (total_lp_bonus * current_prices['bonus_coin']) - total_manual_fees

            if total_investment > 0 and days_active > 0:
                apr = (total_fees / total_investment) * (365 / days_active) * 100
            else:
                apr = 0

        print(f"✔️ Total Fee(+) for {pair.split('-')[0]}: {total_fee_coin1:.6f}")
        print(f"✔️ Total Fee(+) for {pair.split('-')[1]}: {total_fee_coin2:.6f}")
        print(f"✔️ LP Provider Bonus: {total_lp_bonus:.6f}")
        print(f"✔️ Total Manual Fees(-): {total_manual_fees:.2f}")
        print(f"✔️ Investor Paid Fees(-): {total_investor_paid_fees:.2f}")
        print(f"✔️ Loan Paid (USDT): {notional_outstanding_loan:.4f}")
        print(f"✔️ Positive Gain (USDT): {positive_gain_usdt:.2f}")
        print(f"✔️ Average Investment Notional (current prices): {total_investment:.2f}")
        print(f"✔️ Days Active: {days_active:.2f} days")
        print(f"✔️ APY for {pair}: {apr:.2f}%")

        total_weighted_apr += apr * total_investment
        total_investment_all += total_investment

    if total_investment_all > 0:
        overall_apr = total_weighted_apr / total_investment_all
        # print(f"\nThe overall APY for all positions is: {overall_apr:.2f}%\n")
    else:
        print("❌ No active positions to calculate APY.")



@rerunnable
def view_positions():
    temp_pair = ''
    positions = load_positions()
    balance_movements = load_balance_movements()

    if not positions:
        print("❌ No positions available.")
        return

    position_map = {}
    for position in positions:
        position_map.setdefault(position['pair'], []).append(position)

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("📊  CURRENT LIQUIDITY POSITIONS  📊")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    position_list_len = len(position_map.items())
    pair_iterator = 0
    for pair, pos_list in position_map.items():
        pair_iterator += 1
        pair_text = "Pair: " + pair.upper()
        print(f"\n{pair_text}\n")
        total_quantity_1 = sum(pos['initial_quantity_1'] for pos in pos_list)
        total_quantity_2 = sum(pos['initial_quantity_2'] for pos in pos_list)
        total_fee_coin1 = sum(pos['total_fee_coin1'] for pos in pos_list)
        total_fee_coin2 = sum(pos['total_fee_coin2'] for pos in pos_list)
        total_lp_bonus = sum(pos['lp_provider_bonus'] for pos in pos_list)
        total_investor_paid_fees = sum(pos['investor_paid_fees'] for pos in pos_list)

        # Combine fees from manually booked fees
        total_manual_fees = sum(fee['amount'] for pos in pos_list for fee in pos.get('fees', []))

        # Display position data
        for position in pos_list:

            # Sum of investor paid fees and manual fees for this position
            position_manual_fees = sum(fee['amount'] for fee in position.get('fees', []))
            total_fees = position['investor_paid_fees'] + position_manual_fees
            if position['position_status'] == 'Active':
                print(f"✅ Position status: {position['position_status']}\n")
            else:
                print(f"🔴 Position status: {position['position_status']}\n")
            print(f"📌 Date Added {position['date_added']}, "
                  f"Quantity 1: {position['initial_quantity_1']:.2f}, "
                  f"Quantity 2: {position['initial_quantity_2']:.2f}, "
                  f"Fee {pair.split('-')[0]}: {position['total_fee_coin1']:.2f}, "
                  f"Fee {pair.split('-')[1]}: {position['total_fee_coin2']:.2f}, "
                  f"LP Provider Bonus: {position['lp_provider_bonus']:.4f}, "
                  f"Investor Paid Fees: {total_fees:.2f}")



        # Display fees section with manual entries
        fee_count = 0
        for position in pos_list:
            for _ in position.get('fees', []):
                fee_count += 1
        if fee_count > 0:
            print(f"\n💸  FEE DEDUCTED FOR {pair}  💸")
            for position in pos_list:
                for fee in position.get('fees', []):
                    print(f"Amount: {fee['amount']} USDT, Description: {fee['description']}, Date: {fee['date']}\n")
        else:
            print(f"\n💸 No fees were deducted for {pair}")
        print("")
        print(f"✔️ Total Quantity of {pair.split('-')[0]}: {total_quantity_1:.2f}")
        print(f"✔️ Total Quantity of {pair.split('-')[1]}: {total_quantity_2:.2f}")
        print(f"✔️ Total Fee(+) for {pair.split('-')[0]}: {total_fee_coin1:.2f}")
        print(f"✔️ Total Fee(+) for {pair.split('-')[1]}: {total_fee_coin2:.2f}")
        print(f"✔️ Total LP Provider Bonus: {total_lp_bonus:.2f}")
        print(f"✔️ Total Manual Fees(-): {total_manual_fees:.2f}")
        print(f"✔️ Total Investor Paid Fees(-): {total_investor_paid_fees:.2f}")

        if float(position.get('loan_value', 0)) > 0.001:
            print("")
            print(f"🏦 Borrowed value : {position['loan_value']} {position.get('loan_coin', 'Unknow()n')}")

        # Display collateral
        if position.get('colateral_coin_name') and position.get('colateral_notional'):
            print(f"🏦 Collateral: {position['colateral_notional']} {position['colateral_coin_name']}")
        else:
            print(f"🏦 No collateral data added")


        if pair_iterator < position_list_len:
            print('\n             ━━━━━━━━━━━━━━━━━━━━━━━')

    # Display balance movements summary
    if balance_movements:
        # Sort balance movements by 'pair' key
        balance_movements = sorted(balance_movements, key=lambda x: x['pair'])

        temp_pair_name = ''
        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("          🔄  BALANCE MOVEMENTS SUMMARY  🔄")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        for entry in balance_movements:
            if {entry['pair']} != temp_pair_name and temp_pair_name != '':
                print("\n             ━━━━━━━━━━━━━━━━━━━━━━━")
            temp_pair_name = {entry['pair']}
            coin1_name, coin2_name = entry['pair'].split('-')

            # Extract balances based on type
            initial_balances_metamask = entry.get('initial_balances', {}).get('metamask', {})
            initial_balances_lp = entry.get('initial_balances', {}).get('lp', {})

            open_lp_balances_metamask = entry.get('open_lp_balances', {}).get('metamask', {})
            open_lp_balances_lp= entry.get('open_lp_balances', {}).get('lp', {})

            redemption_balances_metamask = entry.get('redemption_balances', {}).get('metamask', {})
            redemption_balances_lp = entry.get('redemption_balances', {}).get('metamask', {})


            print(f"\n📅 Date: {entry['date']}")
            print(f"🔹 Pair: {entry['pair']}")
            print(f"🔸 Type: {entry['type'].capitalize()}")

            if len(initial_balances_lp) > 0:
                print(f"💼 Metamask: {coin1_name}: {initial_balances_metamask.get(coin1_name, 'N/A')}, "
                      f"{coin2_name}: {initial_balances_metamask.get(coin2_name, 'N/A')}")
                print(f"💼 LP: {coin1_name}: {initial_balances_lp.get(coin1_name, 'N/A')}, "
                      f"{coin2_name}: {initial_balances_lp.get(coin2_name, 'N/A')}\n")

            if len(open_lp_balances_lp) > 0:
                print(f"💼 Metamask: {coin1_name}: {open_lp_balances_metamask.get(coin1_name, 'N/A')}, "
                      f"{coin2_name}: {open_lp_balances_metamask.get(coin2_name, 'N/A')}")
                print(f"💼 LP: {coin1_name}: {open_lp_balances_lp.get(coin1_name, 'N/A')}, "
                      f"{coin2_name}: {open_lp_balances_lp.get(coin2_name, 'N/A')}\n")

            if len(redemption_balances_lp) > 0:
                print(f"💼 Metamask: {coin1_name}: {redemption_balances_metamask.get(coin1_name, 'N/A')}, "
                      f"{coin2_name}: {redemption_balances_metamask.get(coin2_name, 'N/A')}")
                print(f"💼 LP: {coin1_name}: {redemption_balances_lp.get(coin1_name, 'N/A')}, "
                      f"{coin2_name}: {redemption_balances_lp.get(coin2_name, 'N/A')}")
    else:
        print("\n❌ No balance movements recorded.")

# Function to create a new position
@rerunnable
def create_new_position():
    pair = get_input("Enter Coin Pair (e.g., USDT-USD+): ", '', colour = "blue")
    coin1_name, coin2_name = pair.split('-')
    loan_coin = ""
    loan_value = 0
    loan_coingecko_id = ''
    positions = load_positions()

    quantity_1 = float(get_input(f"Enter Quantity of {coin1_name}: ", '0', colour = "blue"))
    quantity_2 = float(get_input(f"Enter Quantity of {coin2_name}: ", '0', colour = "blue"))

    date_input = get_input("Enter Date Added (YYYY-MM-DD) or press Enter for today: ", '', colour = "blue")
    date_added = datetime.strptime(date_input, "%Y-%m-%d") if date_input else datetime.now()

    coingecko_id_coin1 = get_coin_id(coin1_name)
    coingecko_id_coin2 = get_coin_id(coin2_name)
    bonus_coin = get_input(f"Provide Bonus Coin id. Press enter for 'pancakeswap-token': ", "pancakeswap-token", colour = "blue")
    position_status = "Active"

    loan_is_true = get_input('Is position subjected to loan? y/n?', "",colour = "blue").lower()
    if loan_is_true == 'y':
        loan_coin = get_input("Provide loan coin name (ex.ETH): ", '', colour = "blue")
        loan_coingecko_id = get_coin_id(loan_coin)
        loan_value = get_input("Provide loan value: ", '0',  colour = "blue")
        colateral_coin_name = get_input("Enter coin name of collateral?","",  colour = "blue")
        colateral_coingecko_id = get_coin_id(colateral_coin_name)
        colateral_notional = float(get_input("Provide collateral qty?", 0, colour = "blue"))

        new_position = {
            'pair': pair,
            'initial_quantity_1': quantity_1,
            'initial_quantity_2': quantity_2,
            'total_fee_coin1': 0,  # No fee initially
            'total_fee_coin2': 0,  # No fee initially
            'lp_provider_bonus': 0,  # No bonus initially
            'investor_paid_fees': 0,  # Investor's paid fees
            'date_added': date_added,
            'id': len(positions) + 1,
            'current_prices': {},
            'fees': [],  # Store manually added fees here
            'loan_coin': loan_coin,
            'loan_value': loan_value,
            'loan_coin_coingecko_id': loan_coingecko_id,
            'coingecko_id_coin1': coingecko_id_coin1,
            'coingecko_id_coin2': coingecko_id_coin2,
            'position_status': position_status,
            'bonus_coin': bonus_coin,
            'colateral_coin_name': colateral_coin_name,
            'colateral_coingecko_id': colateral_coingecko_id,
            'colateral_notional': colateral_notional
        }

    else:
        new_position = {
            'pair': pair,
            'initial_quantity_1': quantity_1,
            'initial_quantity_2': quantity_2,
            'total_fee_coin1': 0,  # No fee initially
            'total_fee_coin2': 0,  # No fee initially
            'lp_provider_bonus': 0,  # No bonus initially
            'investor_paid_fees': 0,  # Investor's paid fees
            'date_added': date_added,
            'id': len(positions) + 1,
            'current_prices': {},
            'fees': [],  # Store manually added fees here
            'coingecko_id_coin1': coingecko_id_coin1,
            'coingecko_id_coin2': coingecko_id_coin2,
            'position_status': position_status,
            'bonus_coin': bonus_coin
        }

    positions.append(new_position)
    print(positions)
    save_positions(positions)

@rerunnable
def modify_last_entry():
    positions = load_positions()
    if not positions:
        print("❌ No positions available to modify.")
        return

    # Create a map of positions by pair
    position_map = {}
    for position in positions:
        position_map.setdefault(position['pair'], []).append(position)

    # Display available pairs to modify the last entry
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("⚙️  SELECT A COIN PAIR TO MODIFY LAST ENTRY  ⚙️")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    for idx, pair in enumerate(position_map.keys(), 1):
        print(f"{idx}. Pair: {pair}")

    selected_idx = int(get_input("Select a pair by number: ", '0'))
    pairs = list(position_map.keys())
    if selected_idx < 1 or selected_idx > len(pairs):
        print("❌ Invalid selection.")
        return

    selected_pair = pairs[selected_idx - 1]
    last_position = position_map[selected_pair][-1]  # Get the last entry for this pair

    # Display the data of the last entry with improved formatting and emojis
    print(f"\n🔄 Last entry for {selected_pair}:")
    print(f"🪙 pair: {last_position['pair']}")
    print(f"📊 initial_quantity_1: {last_position['initial_quantity_1']}")
    print(f"📊 initial_quantity_2: {last_position['initial_quantity_2']}")
    print(f"💰 total_fee_coin1: {last_position['total_fee_coin1']}")
    print(f"💰 total_fee_coin2: {last_position['total_fee_coin2']}")
    print(f"🏅 lp_provider_bonus: {last_position['lp_provider_bonus']}")
    print(f"💸 investor_paid_fees: {last_position['investor_paid_fees']}")
    print(f"🕒 date_added: {last_position['date_added']}")
    print(f"🆔 id: {last_position['id']}")
    print(f"📈 current_prices: {last_position['current_prices']}")
    print(f"✅ Current position status: {last_position['position_status']}")

    # Prompt user to modify each key
    last_position['initial_quantity_1'] = float(get_input(
        f"Enter new Quantity of {selected_pair.split('-')[0]} (or press Enter to keep {last_position['initial_quantity_1']}): ",
        last_position['initial_quantity_1']))
    last_position['initial_quantity_2'] = float(get_input(
        f"Enter new Quantity of {selected_pair.split('-')[1]} (or press Enter to keep {last_position['initial_quantity_2']}): ",
        last_position['initial_quantity_2']))
    last_position['total_fee_coin1'] = float(get_input(
        f"Enter new Fee for {selected_pair.split('-')[0]} (or press Enter to keep {last_position['total_fee_coin1']}): ",
        last_position['total_fee_coin1']))
    last_position['total_fee_coin2'] = float(get_input(
        f"Enter new Fee for {selected_pair.split('-')[1]} (or press Enter to keep {last_position['total_fee_coin2']}): ",
        last_position['total_fee_coin2']))
    last_position['lp_provider_bonus'] = float(
        get_input(f"Enter new LP Provider Bonus (or press Enter to keep {last_position['lp_provider_bonus']}): ",
                  last_position['lp_provider_bonus']))
    last_position['position_status'] = get_input(
        f"Position Active/Closed. Press enter to keep: {last_position['position_status']}: ", "Active")

    # Handle empty input for investor_paid_fees
    new_investor_paid_fees = get_input(
        f"Enter new Investor Paid Fees (or press Enter to keep {last_position['investor_paid_fees']}): ", "")
    if new_investor_paid_fees:
        last_position['investor_paid_fees'] = float(new_investor_paid_fees)

    save_positions(positions)
    print("\n✅ Last entry modified successfully.")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


# Function to modify an existing position
@rerunnable
def modify_position():
    positions = load_positions()
    if not positions:
        print("❌ No positions available to modify.")
        return

    position_map = {}
    for position in positions:
        position_map.setdefault(position['pair'], position)

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("⚙️  SELECT A CRYPTO PAIR TO MODIFY  ⚙️")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    for idx, pair in enumerate(position_map.keys(), 1):
        print(f"{idx}. {pair}")

    selected_idx = int(get_input("Select a pair by number: ", '0'))
    pairs = list(position_map.keys())
    if selected_idx < 1 or selected_idx > len(pairs):
        print("❌ Invalid selection.")
        return

    selected_pair = pairs[selected_idx - 1]
    coin1_name, coin2_name = selected_pair.split('-')

    change_type = get_input("Increase or Decrease position? Enter 'i' for increase, 'd' for decrease: ", 'i').lower()
    if change_type not in ['i', 'd']:
        print("❌ Invalid input. Please enter 'i' or 'd'.")
        return

    quantity_1 = float(
        get_input(f"Enter {'increased' if change_type == 'i' else 'decreased'} Quantity of {coin1_name}: ", '0'))
    quantity_2 = float(
        get_input(f"Enter {'increased' if change_type == 'i' else 'decreased'} Quantity of {coin2_name}: ", '0'))
    if change_type == 'd':
        quantity_1 = -quantity_1
        quantity_2 = -quantity_2

    fee_coin1 = float(get_input(f"Enter Fee for {coin1_name}: ", '0'))
    fee_coin2 = float(get_input(f"Enter Fee for {coin2_name}: ", '0'))

    lp_provider_bonus = float(get_input(f"Enter LP Provider Bonus for {selected_pair}: ", '0'))

    investor_paid_fees = float(get_input(f"Enter Investor Paid Fees: ", '0'))

    for pos in positions:
        if pos['pair'] == selected_pair:
            pos['initial_quantity_1'] += quantity_1
            pos['initial_quantity_2'] += quantity_2
            pos['total_fee_coin1'] += fee_coin1
            pos['total_fee_coin2'] += fee_coin2
            pos['lp_provider_bonus'] += lp_provider_bonus
            pos['investor_paid_fees'] += investor_paid_fees
            break

    save_positions(positions)
    print("\n✅ Position modified successfully.")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


# Function to delete all entries
@rerunnable
def delete_all_positions():
    confirm = get_input(f"❓ Are you sure you want to delete all positions? (y/n): ", 'n').lower()
    if confirm == 'y':
        if os.path.exists(DATA_FILE) and os.path.exists(REBALANCE_FILE) and os.path.exists(LP_NOTIONALS_FILE):
            os.remove(DATA_FILE)

            print("\n✅ All positions have been deleted.")
        else:
            print("❌ No positions to delete.")
    else:
        print("❌ Deletion cancelled.")


# Function to delete a position or all positions
@rerunnable
def delete_position():
    positions = load_positions()
    if not positions:
        print("❌ No positions available to delete.")
        return

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"0. Delete all: {len(positions)} entries")

    for idx, position in enumerate(positions, 1):
        print(f"{idx}. ID: {position['id']}, Pair: {position['pair']}, Date Added: {position['date_added']}")

    selected_idx = int(get_input("Select a position to delete by number (or 0 to delete all): ", '0'))

    if selected_idx == 0:
        delete_all_positions()
    elif selected_idx < 1 or selected_idx > len(positions):
        print("❌ Invalid selection.")
        return
    else:
        confirm = get_input(f"❓ Are you sure you want to delete position {selected_idx}? (y/n): ", 'n').lower()
        if confirm == 'y':
            deleted_position = positions.pop(selected_idx - 1)
            save_positions(positions)
            print(f"\n✅ Position ID {deleted_position['id']} has been deleted.")
        else:
            print("❌ Deletion cancelled.")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

@rerunnable
def calculate_rolling_correlation(df, window_size=30):
    """
    Calculate the rolling correlation between price1 and price2 over the specified window size (in hours).
    """
    rolling_corr = df['price1'].rolling(window=window_size).corr(df['price2'])
    return rolling_corr


@rerunnable
def apply_moving_average(rolling_corr, smoothing_window=10):
    """
    Apply a simple moving average to the rolling correlation data to reduce noise.
    """
    smoothed_corr = rolling_corr.rolling(window=smoothing_window).mean()
    return smoothed_corr


@rerunnable
def plot_rolling_correlation(rolling_corr, window_size, coin1_name, coin2_name):
    """
    Plot the rolling correlation between two assets and print key statistics.
    """
    mean_correlation = rolling_corr.mean()
    std_correlation = rolling_corr.std()
    min_correlation = rolling_corr.min()
    max_correlation = rolling_corr.max()

    print(f"\nRolling Correlation Statistics (Window size: {window_size} hours):")
    print(f"- Mean Correlation: {mean_correlation:.4f}")
    print(f"- Standard Deviation: {std_correlation:.4f}")
    print(f"- Minimum Correlation: {min_correlation:.4f}")
    print(f"- Maximum Correlation: {max_correlation:.4f}")

    plt.figure(figsize=(12, 6))
    plt.plot(rolling_corr.index, rolling_corr, label=f'{window_size}-hour Rolling Correlation', color='indigo')
    plt.axhline(0, color='gray', linestyle='--')
    plt.axhline(1, color='green', linestyle='--', label='Perfect Positive Correlation')
    plt.axhline(-1, color='red', linestyle='--', label='Perfect Negative Correlation')
    plt.axhline(mean_correlation, color='magenta', linestyle='-', label='Mean Correlation')
    plt.xlabel('Date')
    plt.ylabel('Rolling Correlation')
    plt.title(f'Rolling Correlation between {coin1_name} and {coin2_name}')
    plt.legend()
    plt.tight_layout()
    plt.show()


@rerunnable
def plot_noise_reduction(rolling_corr, smoothed_corr, coin1_name, coin2_name):
    """
    Plot the noise-reduced correlation using moving average and print key statistics.
    """
    mean_smoothed_corr = smoothed_corr.mean()
    std_smoothed_corr = smoothed_corr.std()
    min_smoothed_corr = smoothed_corr.min()
    max_smoothed_corr = smoothed_corr.max()

    print(f"\nSmoothed Correlation Statistics:")
    print(f"- Mean Smoothed Correlation: {mean_smoothed_corr:.4f}")
    print(f"- Standard Deviation: {std_smoothed_corr:.4f}")
    print(f"- Minimum Smoothed Correlation: {min_smoothed_corr:.4f}")
    print(f"- Maximum Smoothed Correlation: {max_smoothed_corr:.4f}")

    plt.figure(figsize=(12, 6))
    plt.plot(rolling_corr.index, rolling_corr, label='Original Rolling Correlation', color='lightgray', alpha=0.7)
    plt.plot(smoothed_corr.index, smoothed_corr, label='Smoothed Correlation', color='blue')
    plt.axhline(0, color='gray', linestyle='--')
    plt.axhline(1, color='green', linestyle='--', label='Perfect Positive Correlation')
    plt.axhline(-1, color='red', linestyle='--', label='Perfect Negative Correlation')
    plt.xlabel('Date')
    plt.ylabel('Smoothed Correlation')
    plt.title(f'Smoothed Correlation for {coin1_name} and {coin2_name}')
    plt.legend()
    plt.tight_layout()
    plt.show()


@rerunnable
def analyze_pair_performance():
    """
    Analyzes and plots the price ratio, daily returns, expected price range based on standard deviation,
    identifies the most popular daily return range, and calculates the rolling correlation between two coins.
    """
    # Input Block
    try:
        # Get user input for coins and days
        coin1_name = input("Enter the name or symbol of the first coin: ").strip().upper()
        coin2_name = input("Enter the name or symbol of the second coin: ").strip().upper()
        days_input = input("Enter the number of days back to fetch data (between 1 and 90): ").strip()
        try:
            days = int(days_input)
            if days < 1 or days > 90:
                print("Days must be between 1 and 90.")

        except ValueError:
            print("Invalid number of days.")

        # Get CoinGecko IDs
        coin1_id = get_coin_id(coin1_name)
        if not coin1_id:
            coin1_id = input(
                f"Couldn't find CoinGecko ID for '{coin1_name}'. Please enter it manually (or type 'exit' to quit): ").strip()
        coin2_id = get_coin_id(coin2_name)
        if not coin2_id:
            coin2_id = input(
                f"Couldn't find CoinGecko ID for '{coin2_name}'. Please enter it manually (or type 'exit' to quit): ").strip()

        # Fetch price data
        print("\nFetching data, please wait...")
        df1 = fetch_coin_prices(coin1_id, days)
        df2 = fetch_coin_prices(coin2_id, days)

        if df1 is None or df2 is None:
            print("Failed to fetch price data.", color ="red")

        # Resample both DataFrames to hourly frequency
        df1_resampled = df1.resample('h').mean()
        df2_resampled = df2.resample('h').mean()

        # Join the resampled DataFrames
        df = df1_resampled.join(df2_resampled, lsuffix='_price1', rsuffix='_price2', how='inner')
        df.rename(columns={'price_price1': 'price1', 'price_price2': 'price2'}, inplace=True)
        df.dropna(subset=['price1', 'price2'], inplace=True)

    except KeyboardInterrupt:
        print("Process interrupted by user.")
        sys.exit(1)

    # Global variable for liquidation price
    liquidation_price_presence = input("Is a liquidation price applicable? (y/n): ",color = "blue").strip().lower()
    if liquidation_price_presence == 'y':
        liquidation_price_presence = input(f"Enter the liquidation price for {coin1_name}/{coin2_name}: ", color = "blue").strip().replace(',', '.')
    else:
        liquidation_price_presence = None

    # Calculate price ratio
    df['price_ratio'] = df['price1'] / df['price2']

    # Log initial DataFrame details
    print(f"\nInitial DataFrame size: {df.shape}")
    print(f"DataFrame columns: {list(df.columns)}")
    print("Data types:")
    print(df.dtypes)
    print("\nHead of the DataFrame:")
    print(df.head())

    # **First Plot: Price Ratio Over Time**
    plt.figure(figsize=(12, 6))
    plt.plot(df.index, df['price_ratio'], label=f'{coin1_name}/{coin2_name} Price Ratio', color='blue')
    plt.xlabel('Date')
    plt.ylabel(f'Price Ratio ({coin1_name}/{coin2_name})')
    plt.title(f'{coin1_name}/{coin2_name} Price Ratio Over Time')
    plt.legend()
    plt.tight_layout()
    plt.show()

    # Resample to daily data (since data is hourly)
    df_daily = df['price_ratio'].resample('D').last()

    # Convert df_daily to a DataFrame
    df_daily = df_daily.to_frame(name='price_ratio')

    # Remove frequency from index to avoid errors during filtering
    df_daily.index.freq = None

    # Ensure positive price ratios
    df_daily = df_daily[df_daily['price_ratio'] > 0]

    # Calculate daily log returns
    df_daily['log_return'] = np.log(df_daily['price_ratio'] / df_daily['price_ratio'].shift(1))
    df_daily.dropna(inplace=True)

    # Log DataFrame after processing
    print(f"\nCalculated 'price_ratio'.")
    print(f"Resampled to daily data. df_daily size: {df_daily.shape}")
    print(f"Filtered positive 'price_ratio'. df_daily size after filtering: {df_daily.shape}")
    print(f"Number of NaN values in 'price_ratio': {df_daily['price_ratio'].isna().sum()}")
    print(f"Calculated 'log_return'. df_daily size after dropna: {df_daily.shape}")
    print(f"Number of NaN values in 'log_return': {df_daily['log_return'].isna().sum()}")
    print(f"Head of df_daily after log return calculation:")
    print(df_daily.head())

    # Calculate the number of days of data
    num_days = (df_daily.index[-1] - df_daily.index[0]).days
    print(f"\nData covers {num_days} days.")

    # Calculate mean and standard deviation of daily log returns
    mu_daily = df_daily['log_return'].mean()
    sigma_daily = df_daily['log_return'].std()

    # Provide logging with statistical measures
    print(f"\nStatistical Measures:")
    print(f"- Mean of daily log returns: {mu_daily:.6f}")
    print(f"- Standard deviation of daily log returns: {sigma_daily:.6f}")

    # 1. Plot the Gaussian (normal) distribution of daily log returns
    plt.figure(figsize=(12, 6))
    n, bins, patches = plt.hist(df_daily['log_return'], bins=30, density=True, alpha=0.6, color='green')

    # Plot Gaussian fit line
    mu_hist = mu_daily
    sigma_hist = sigma_daily
    xmin, xmax = plt.xlim()
    x = np.linspace(xmin, xmax, 100)
    p = np.exp(-((x - mu_hist) ** 2) / (2 * sigma_hist ** 2)) / (sigma_hist * np.sqrt(2 * np.pi))
    plt.plot(x, p, 'k', linewidth=2, label='Gaussian Fit')

    # Calculate the most frequent daily return range
    counts, bin_edges = np.histogram(df_daily['log_return'], bins=30)
    max_count_index = np.argmax(counts)
    most_frequent_range = (bin_edges[max_count_index], bin_edges[max_count_index + 1])

    # Highlight the most frequent bin in the histogram
    plt.axvspan(most_frequent_range[0], most_frequent_range[1], color='yellow', alpha=0.3, label='Most Frequent Range')

    plt.title(f'Gaussian Distribution of Daily Log Returns: {coin1_name} / {coin2_name}')
    plt.xlabel('Daily Log Return')
    plt.ylabel('Density')
    plt.legend(loc='upper right')
    plt.tight_layout()
    plt.show()

    # Provide logging for the most popular daily return range
    print(f"\nMost Popular Daily Return Range:")
    print(f"- Range: {most_frequent_range[0]:.6f} to {most_frequent_range[1]:.6f}")
    print(f"- Occurrences: {counts[max_count_index]}")

    # 2. Expected price range based on cumulative mean and standard deviation over num_days from the current price
    current_price_ratio = df['price_ratio'].iloc[-1]  # Last know()n price ratio

    # Adjust mean and standard deviation for the number of days
    mu_cumulative = mu_daily * num_days
    sigma_cumulative = sigma_daily * np.sqrt(num_days)

    # Provide logging with cumulative statistical measures
    print(f"\nCumulative Statistical Measures over {num_days} days:")
    print(f"- Cumulative mean (μ * N): {mu_cumulative:.6f}")
    print(f"- Cumulative standard deviation (σ * sqrt(N)): {sigma_cumulative:.6f}")

    # Expected future price ratio after num_days
    expected_price_ratio = current_price_ratio * np.exp(mu_cumulative)

    # Calculate the expected price range
    lower_bound = expected_price_ratio * np.exp(-sigma_cumulative)
    upper_bound = expected_price_ratio * np.exp(sigma_cumulative)

    print(f"\nExpected Future Price Ratio after {num_days} days:")
    print(f"- Expected Price Ratio: {expected_price_ratio:.4f}")
    print(f"- Lower Bound (1 Std Dev): {lower_bound:.4f}")
    print(f"- Upper Bound (1 Std Dev): {upper_bound:.4f}")
    print(f"With 68% certainty, the price ratio will be within this range.")

    # 3. Plot the price ratio and expected price range on the same chart
    plt.figure(figsize=(12, 6))

    # Plot price ratio over time
    plt.plot(df.index, df['price_ratio'], label=f'{coin1_name}/{coin2_name} Price Ratio', color='blue', alpha=0.7)

    # Plot upper and lower bounds for expected price range
    plt.axhline(y=upper_bound, color='red', linestyle='--', label=f'Upper Bound ({num_days} Days, 1 Std Dev)')
    plt.axhline(y=lower_bound, color='green', linestyle='--', label=f'Lower Bound ({num_days} Days, 1 Std Dev)')
    plt.axhline(y=expected_price_ratio, color='purple', linestyle='--', label=f'Expected Price in {num_days} Days')

    # Include liquidation price if applicable
    try:
        if liquidation_price_presence is not None and float(liquidation_price_presence) > 0.01:
            plt.axhline(y=float(liquidation_price_presence), color='magenta', linestyle='-', label='Liquidation Price')
    except Exception as e:
        pass

    # Mark the current price ratio
    plt.axhline(y=current_price_ratio, color='orange', linestyle='-', label='Current Price Ratio')

    # Set labels and title
    plt.xlabel('Date')
    plt.ylabel(f'Price Ratio ({coin1_name}/{coin2_name})')
    plt.title(f'{coin1_name}/{coin2_name} Price Ratio with Expected {num_days}-Day Price Range')
    plt.legend(loc='upper left')
    plt.tight_layout()
    plt.show()

    # **Correlation Measure**

    # Get the window size for rolling correlation from the user
    window_size_input = input(
        "Enter the rolling window size in hours for correlation calculation (e.g., 24, 48, 72): ").strip()
    try:
        window_size = int(window_size_input)
    except ValueError:
        print("Invalid input. Using default window size of 24 hours.")
        window_size = 24  # default value

    # Calculate rolling correlation
    rolling_corr = calculate_rolling_correlation(df, window_size=window_size)

    # Plot rolling correlation and print statistics
    plot_rolling_correlation(rolling_corr, window_size, coin1_name, coin2_name)

    # Apply smoothing using Moving Average
    # smoothing_window_input = input("Enter the smoothing window size for moving average (e.g., 10): ").strip()
    smoothing_window_input = window_size_input

    try:
        smoothing_window = int(smoothing_window_input)
    except ValueError:
        print("Invalid input. Using default smoothing window size of 10.")
        smoothing_window = 10
    smoothed_corr = apply_moving_average(rolling_corr, smoothing_window=smoothing_window)

    # Plot smoothed correlation and print statistics
    plot_noise_reduction(rolling_corr, smoothed_corr, coin1_name, coin2_name)

    # **Additional Functionality: Price Ratio Distribution**

    # Ask the user for custom rounding precision
    print("\nYou can enter a custom rounding precision (e.g., 0.01, 0.001, 0.005, 10, 50).")
    rounding_input = input("Enter the rounding precision. Press Enter to use 0.01 by default: ").strip().replace(',',
                                                                                                                 '.')
    if rounding_input == '':
        precision_value = 0.01  # Default to 0.01
        rounding_precision = 2  # Number of decimal places
    else:
        try:
            precision_value = float(rounding_input)
            if precision_value <= 0:
                print("Invalid precision value. Must be greater than 0. Defaulting to 0.01.")
                precision_value = 0.01
                rounding_precision = 2
            else:
                # Determine the number of decimal places if precision_value is a decimal
                if '.' in rounding_input:
                    import decimal
                    rounding_precision = abs(decimal.Decimal(str(precision_value)).as_tuple().exponent)
                else:
                    rounding_precision = 0
        except (ValueError, decimal.InvalidOperation):
            print("Invalid input. Defaulting to rounding precision of 0.01.")
            precision_value = 0.01
            rounding_precision = 2

    # Round the price ratios according to the user's choice
    df['price_ratio_rounded'] = (df['price_ratio'] / precision_value).round(0) * precision_value

    # Count the number of occurrences of each rounded price ratio
    price_counts = df['price_ratio_rounded'].value_counts().sort_index()

    # Plot the counts with prices on x-axis in ascending order
    plt.figure(figsize=(12, 6))
    price_counts.plot(kind='bar')
    plt.xlabel(f'Price Ratio (Rounded to nearest {precision_value})')
    plt.ylabel('Number of Occurrences')
    plt.title(f"Distribution of Price Ratios for {coin1_name}/{coin2_name}")
    plt.xticks(rotation=90)
    plt.tight_layout()
    plt.show()

    # Identify the most frequent price ratios
    max_count = price_counts.max()
    most_frequent_prices = price_counts[price_counts == max_count].index.tolist()

    # Display the results
    print("\nMost frequent price ratio(s):")
    for price in most_frequent_prices:
        # Format the price based on rounding_precision
        if rounding_precision > 0:
            print(f"- {price:.{rounding_precision}f} (Occurrences: {max_count})")
        else:
            print(f"- {price:.0f} (Occurrences: {max_count})")

    print("\nConsider focusing on these price ratio values when providing liquidity to the pool.")


# New function added here
@rerunnable
def calculate_loan_vs_position_discrepancy():
    """
    Calculates how the current value of assets relates to the loaned amount.
    """

    # Ask the user whether they want to input data manually or select from positions
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("📊  CALCULATE LOAN VS POSITION DISCREPANCY  📊")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("1. Select from available pairs where loan was applicable")
    print("2. Manually input loan and asset data")

    choice = input("\nSelect an option (1 or 2): ").strip()

    if choice == '2':
        # Existing manual input code
        # Ask for loaned coin and amount
        loaned_coin_name = get_input("Enter the loaned coin name: ", '').strip()
        loaned_coin_id = get_coin_id(loaned_coin_name)
        if not loaned_coin_id:
            print("Invalid coin. Please try again.")
            return
        loaned_amount_input = get_input("Enter the loaned amount: ", '0').replace(',', '.')
        try:
            loaned_amount = float(loaned_amount_input)
        except ValueError:
            print("Invalid amount. Please try again.")
            return

        # Ask for current assets and balances
        asset1_name = get_input("Enter the name of asset1: ", '').strip()
        asset1_id = get_coin_id(asset1_name)
        if not asset1_id:
            print("Invalid asset1 coin. Please try again.")
            return
        asset1_balance_input = get_input(f"Enter the balance of {asset1_name}: ", '0').replace(',', '.')
        try:
            asset1_balance = float(asset1_balance_input)
        except ValueError:
            print("Invalid balance. Please try again.")
            return

        asset2_name = get_input("Enter the name of asset2: ", '').strip()
        asset2_id = get_coin_id(asset2_name)
        if not asset2_id:
            print("Invalid asset2 coin. Please try again.")
            return
        asset2_balance_input = get_input(f"Enter the balance of {asset2_name}: ", '0').replace(',', '.')
        try:
            asset2_balance = float(asset2_balance_input)
        except ValueError:
            print("Invalid balance. Please try again.")
            return

        # Fetch latest prices
        loaned_coin_price = get_latest_price(loaned_coin_id)
        asset1_price = get_latest_price(asset1_id)
        asset2_price = get_latest_price(asset2_id)

        if loaned_coin_price is None or asset1_price is None or asset2_price is None:
            print("Failed to fetch prices. Please try again.")
            return

        # Calculate total value
        loaned_value = loaned_amount * loaned_coin_price
        asset1_value = asset1_balance * asset1_price
        asset2_value = asset2_balance * asset2_price
        total_assets_value = asset1_value + asset2_value

        # Calculate discrepancy
        discrepancy = total_assets_value - loaned_value
        discrepancy_percentage = (discrepancy / loaned_value) * 100

        # Display results
        print("\nLoaned Coin:")
        print(
            f" - {loaned_coin_name}: Amount = {loaned_amount}, Price = {loaned_coin_price:.2f}, Total Value = {loaned_value:.2f}")
        print("\nCurrent Assets:")
        print(f" - {asset1_name}: Balance = {asset1_balance}, Price = {asset1_price:.2f}, Value = {asset1_value:.2f}")
        print(f" - {asset2_name}: Balance = {asset2_balance}, Price = {asset2_price:.2f}, Value = {asset2_value:.2f}")
        print(f"Total Assets Value: {total_assets_value:.2f}")

        print("\nDiscrepancy:")
        if discrepancy > 0:
            print(f"Your assets are valued {discrepancy_percentage:.2f}% MORE than the loaned amount.")
        else:
            print(f"Your assets are valued {abs(discrepancy_percentage):.2f}% LESS than the loaned amount.")


    elif choice == '1':

        # Load positions

        positions = load_positions()

        if not positions:
            print("❌ No positions available.")

            return

        # Filter positions where loan was applicable (loan_value > 0)

        loan_positions = [pos for pos in positions if float(pos.get('loan_value', 0)) > 0]

        if not loan_positions:
            print("❌ No positions with loans available.")

            return

        # Create a map of positions by pair

        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        print("📋  AVAILABLE POSITIONS WITH LOANS  📋")

        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        position_map = {}

        for idx, position in enumerate(loan_positions, 1):
            position_map[idx] = position

            print(
                f"{idx}. Pair: {position['pair']}, Loan Coin: {position['loan_coin']}, Loan Value: {position['loan_value']}, Date Added: {position['date_added']}")

        # Let the user select one

        selected_idx_input = get_input("Select a position by number: ", '0').strip()

        try:

            selected_idx = int(selected_idx_input)

            if selected_idx not in position_map:
                print("❌ Invalid selection.")

                return

        except ValueError:

            print("❌ Invalid input. Please enter a number.")

            return

        selected_position = position_map[selected_idx]

        # Extract data from the selected position

        # Loaned coin name and coingecko id

        loaned_coin_name = selected_position.get('loan_coin')

        loaned_coin_id = selected_position.get('loan_coin_coingecko_id')

        loaned_amount = float(selected_position.get('loan_value', 0))

        if not loaned_coin_name or not loaned_coin_id or loaned_amount <= 0:
            print("❌ Loan information is incomplete in the selected position.")

            return

        # Assets and balances

        asset1_name, asset2_name = selected_position['pair'].split('-')

        asset1_id = selected_position.get('coingecko_id_coin1')

        asset2_id = selected_position.get('coingecko_id_coin2')

        if not asset1_id or not asset2_id:
            print("❌ Asset coin IDs are missing in the selected position.")

            return

        # Prompt user for current quantities of asset1 and asset2

        asset1_balance_input = get_input(f"Enter the current balance of {asset1_name}: ", '0').replace(',', '.')

        try:

            asset1_balance = float(asset1_balance_input)

        except ValueError:

            print("Invalid balance. Please try again.")

            return

        asset2_balance_input = get_input(f"Enter the current balance of {asset2_name}: ", '0').replace(',', '.')

        try:

            asset2_balance = float(asset2_balance_input)

        except ValueError:

            print("Invalid balance. Please try again.")

            return

        # Load balance movements to check for uninvested balances

        balance_movements = load_balance_movements()

        if balance_movements:

            # Filter movements for the selected pair

            pair_movements = [entry for entry in balance_movements if entry['pair'] == selected_position['pair']]

            if pair_movements:
                # Get the latest movement

                latest_movement = pair_movements[-1]

                uninvested_asset1 = latest_movement['metamask_balances'][asset1_name]

                uninvested_asset2 = latest_movement['metamask_balances'][asset2_name]

                # Subtract uninvested balances from the current balances

                asset1_balance += uninvested_asset1

                asset2_balance += uninvested_asset2

        # Fetch latest prices

        loaned_coin_price = get_latest_price(loaned_coin_id)

        asset1_price = get_latest_price(asset1_id)

        asset2_price = get_latest_price(asset2_id)

        if loaned_coin_price is None or asset1_price is None or asset2_price is None:
            print("Failed to fetch prices. Please try again.")

            return

        # Calculate total value

        loaned_value = loaned_amount * loaned_coin_price

        asset1_value = asset1_balance * asset1_price

        asset2_value = asset2_balance * asset2_price

        total_assets_value = asset1_value + asset2_value

        total_assets_value_in_loaned_coin_denominated = (asset1_value + asset2_value) / loaned_coin_price

        # Calculate discrepancy

        discrepancy = total_assets_value - loaned_value

        discrepancy_percentage = (discrepancy / loaned_value) * 100

        # Display results

        print("\nLoaned Coin:")

        print(
            f" - {loaned_coin_name}: Amount = {loaned_amount}, Price = {loaned_coin_price:.2f}, Total Value = {loaned_value:.2f}")

        print("\nCurrent Assets (including uninvested balances):")

        print(f" - {asset1_name}: Balance = {asset1_balance}, Price = {asset1_price:.2f}, Value = {asset1_value:.2f}")

        print(f" - {asset2_name}: Balance = {asset2_balance}, Price = {asset2_price:.2f}, Value = {asset2_value:.2f}")

        print(f"Total Assets Value USDT: {total_assets_value:.2f}")
        print(f"Total Assets Value {loaned_coin_name}: {total_assets_value_in_loaned_coin_denominated:.5f}")
        print("\nDiscrepancy:")

        if discrepancy > 0:

            print(f"Your assets are valued {discrepancy_percentage:.2f}% MORE than the loaned amount.")

        else:

            print(f"Your assets are valued {abs(discrepancy_percentage):.2f}% LESS than the loaned amount.")

    else:

        print("❌ Invalid choice. Please enter 1 or 2.")

        return


@rerunnable
def log_current_lp_notionals():
    """
    Log current LP notionals for an existing pair.
    """
    positions = load_positions()
    if not positions:
        print("❌ No positions available.")
        return

    # Display options to the user
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("📝  LOG CURRENT LP NOTIONALS  📝")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("1. Add new notionals entry")
    print("2. Delete old notionals entry")

    choice = input("\nSelect an option (1 or 2): ").strip()
    if choice == '1':
        # Proceed to add new notionals entry

        # Create a map of positions by pair
        position_map = {}
        for position in positions:
            position_map[position['pair']] = position  # Assuming one position per pair

        # Display available pairs
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("🔹  SELECT A PAIR TO LOG NOTIONALS  🔹")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        for idx, pair in enumerate(position_map.keys(), 1):
            print(f"{idx}. {pair}")

        selected_idx = int(get_input("Select a pair by number: ", '0'))
        pairs = list(position_map.keys())
        if selected_idx < 1 or selected_idx > len(pairs):
            print("❌ Invalid selection.")
            return

        selected_pair = pairs[selected_idx - 1]
        coin1_name, coin2_name = selected_pair.split('-')
        coin1_id = position_map[selected_pair]['coingecko_id_coin1']
        coin2_id = position_map[selected_pair]['coingecko_id_coin2']

        # Prompt user for current quantities
        quantity_1 = float(get_input(f"Enter current Quantity of {coin1_name}: ", '0').replace(',', '.'))
        quantity_2 = float(get_input(f"Enter current Quantity of {coin2_name}: ", '0').replace(',', '.'))

        # Prompt user for current APR
        current_apr = float(get_input("Enter current APR (%): ", '0').replace(',', '.'))

        # Fetch latest prices
        price_coin1 = get_latest_price(coin1_id)
        price_coin2 = get_latest_price(coin2_id)

        if price_coin1 is None or price_coin2 is None:
            print("Failed to fetch prices. Please try again.")
            return

        # Calculate current LP valuation
        valuation = quantity_1 * price_coin1 + quantity_2 * price_coin2
        proportion = quantity_1 * price_coin1 / valuation

        # Load existing LP notionals
        lp_notionals = load_lp_notionals()

        # Append new data
        lp_notionals.append({
            'pair': selected_pair,
            'date': datetime.now(),
            'quantity_1': quantity_1,
            'quantity_2': quantity_2,
            'valuation': valuation,
            'proportion': proportion,
            'apr': current_apr
        })

        # Save updated LP notionals
        save_lp_notionals(lp_notionals)

        # Filter data for the selected pair
        pair_data = [entry for entry in lp_notionals if entry['pair'] == selected_pair]

        # Prepare data for plotting
        dates = [entry['date'] for entry in pair_data]
        quantities_1 = [entry['quantity_1'] for entry in pair_data]
        quantities_2 = [entry['quantity_2'] for entry in pair_data]
        valuations = [entry['valuation'] for entry in pair_data]
        aprs = [entry['apr'] for entry in pair_data]

        # Plot quantities and total valuation
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))

        # Plot quantities of both coins
        ax1.plot(dates, quantities_1, label=f'{coin1_name} Quantity', color='blue', marker='o')
        ax1.plot(dates, quantities_2, label=f'{coin2_name} Quantity', color='green', marker='o')
        ax1.set_xlabel('Date')
        ax1.set_ylabel('Quantities')
        ax1.legend(loc='upper left')
        ax1.set_title(f'Quantities of {coin1_name} and {coin2_name} Over Time')
        ax1.grid(True)

        # Format x-axis dates
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.setp(ax1.get_xticklabels(), rotation=45, ha='right')

        # Plot total valuation and APR
        ax2.plot(dates, valuations, label='Total Valuation (USD)', color='red', marker='o')
        ax2.set_xlabel('Date')
        ax2.set_ylabel('Valuation (USD)', color='red')
        ax2.tick_params(axis='y', labelcolor='red')
        ax2.legend(loc='upper left')
        ax2.grid(True)

        # Create a twin axis to plot APR
        ax3 = ax2.twinx()
        ax3.plot(dates, aprs, label='APR (%)', color='purple', marker='x')
        ax3.set_ylabel('APR (%)', color='purple')
        ax3.tick_params(axis='y', labelcolor='purple')
        ax3.legend(loc='upper right')

        # Format x-axis dates
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.setp(ax2.get_xticklabels(), rotation=45, ha='right')

        plt.tight_layout()
        plt.show()

    elif choice == '2':
        # Proceed to delete old notionals entry
        # Load existing LP notionals
        lp_notionals = load_lp_notionals()
        if not lp_notionals:
            print("❌ No LP notionals entries to delete.")
            return

        # List all entries
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("🗑️  DELETE LP NOTIONALS ENTRY  🗑️")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        for idx, entry in enumerate(lp_notionals, 1):
            date_str = entry['date'].strftime("%Y-%m-%d %H:%M")
            print(f"{idx}. 📅 Date: {date_str}, 🔹 Pair: {entry['pair']}, 💰 Valuation: {entry['valuation']:.2f} USD")

        # Prompt user to select entry to delete
        selected_idx = int(get_input("Select an entry to delete by number: ", '0'))
        if selected_idx < 1 or selected_idx > len(lp_notionals):
            print("❌ Invalid selection.")
            return

        # Confirm deletion
        confirm = get_input(f"Are you sure you want to delete entry {selected_idx}? (y/n): ", 'n').lower()
        if confirm == 'y':
            deleted_entry = lp_notionals.pop(selected_idx - 1)
            save_lp_notionals(lp_notionals)
            print(f"\n✅ Entry for pair {deleted_entry['pair']} on {deleted_entry['date']} has been deleted.")
        else:
            print("❌ Deletion cancelled.")

    else:
        print("❌ Invalid selection.")
        return


@rerunnable
def calculate_cointegration():
    """
    Calculate the cointegration between two coins with user input or selection from available pairs.
    """
    # Step 1: User input for coin names or existing pairs
    print("1. Use existing pairs")
    input_method = input("2. Find pairs on Coingecko").strip().lower()

    if input_method == '1':
        positions = load_positions()
        if positions:
            print("\nAvailable pairs from positions:")
            unique_pairs = set([pos['pair'] for pos in positions])
            for idx, pair in enumerate(unique_pairs, 1):
                print(f"{idx}. {pair}")

            selected_idx = int(get_input("Select a pair by number: ", '0'))
            pairs = list(unique_pairs)
            if selected_idx < 1 or selected_idx > len(pairs):
                print("❌ Invalid selection.")
                return

            selected_pair = pairs[selected_idx - 1]
            coin1_name, coin2_name = selected_pair.split('-')
        else:
            print("❌ No positions available.")
            return
    else:
        coin1_name = get_input("Enter the name or symbol of the first coin: ", '').strip().upper()
        coin2_name = get_input("Enter the name or symbol of the second coin: ", '').strip().upper()

    # Step 2: Fetch price data
    days = int(get_input("Enter the number of days back to fetch data (between 1 and 90): ", '30'))
    if days < 1 or days > 90:
        print("❌ Days must be between 1 and 90.")
        return

    coin1_id = get_coin_id(coin1_name)
    if not coin1_id:
        print(f"Invalid coin: {coin1_name}")
        return

    coin2_id = get_coin_id(coin2_name)
    if not coin2_id:
        print(f"Invalid coin: {coin2_name}")
        return

    print("\nFetching data, please wait...")
    df1 = fetch_coin_prices(coin1_id, days)
    df2 = fetch_coin_prices(coin2_id, days)

    if df1 is None or df2 is None:
        print("Failed to fetch price data.")
        return

    df1_resampled = df1.resample('D').last()
    df2_resampled = df2.resample('D').last()
    df = pd.merge(df1_resampled, df2_resampled, left_index=True, right_index=True, suffixes=('_coin1', '_coin2'))

    # Step 3: Linear regression (manual calculation)
    X = df['price_coin2'].values
    y = df['price_coin1'].values
    n = len(X)

    mean_x = sum(X) / n
    mean_y = sum(y) / n

    covariance_xy = sum((X[i] - mean_x) * (y[i] - mean_y) for i in range(n))
    variance_x = sum((X[i] - mean_x) ** 2 for i in range(n))

    slope = covariance_xy / variance_x
    intercept = mean_y - slope * mean_x

    print("\nCalculating linear regression coefficients:")
    print(f"- Mean of X: {mean_x:.4f}")
    print(f"- Mean of Y: {mean_y:.4f}")
    print(f"- Slope (Beta): {slope:.4f}")
    print(f"- Intercept: {intercept:.4f}")

    # Step 4: Calculate residuals
    residuals = [y[i] - (slope * X[i] + intercept) for i in range(n)]
    mean_residual = sum(residuals) / len(residuals)
    print(f"- Mean of residuals: {mean_residual:.4f}")

    # Step 5: Stationarity check (basic manual test)
    def is_stationary_manual(residuals, threshold=0.05):
        mean_residual = sum(residuals) / len(residuals)
        std_dev_residual = (sum((r - mean_residual) ** 2 for r in residuals) / len(residuals)) ** 0.5

        within_std_dev = sum(1 for r in residuals if abs(r - mean_residual) < std_dev_residual) / len(residuals)
        print(f"- Proportion of residuals within one standard deviation: {within_std_dev:.4%}")
        return within_std_dev > (1 - threshold)

    stationary = is_stationary_manual(residuals)

    # Step 6: Calculate average time to return to median spread
    df['Spread'] = df['price_coin1'] - (slope * df['price_coin2'] + intercept)
    median_spread = df['Spread'].median()
    times_to_return = []

    for i in range(1, len(df)):
        if (df['Spread'].iloc[i - 1] > median_spread and df['Spread'].iloc[i] <= median_spread) or \
                (df['Spread'].iloc[i - 1] < median_spread and df['Spread'].iloc[i] >= median_spread):
            times_to_return.append(i)

    avg_time_to_return = np.mean(np.diff(times_to_return)) if len(times_to_return) > 1 else float('inf')
    print(f"- Average time to return to median spread: {avg_time_to_return:.2f} days")

    # Step 7: Log results and conclusion
    print("\nCointegration Test (Manual Calculation):")
    print(f"- Slope: {slope:.4f}")
    print(f"- Intercept: {intercept:.4f}")
    print("The series are cointegrated." if stationary else "The series are not cointegrated.")

    # Step 8: Create the plots
    # A) Plot the coin prices
    plt.figure(figsize=(14, 9))
    plt.subplot(3, 1, 1)
    plt.plot(df.index, df['price_coin1'], label=f'{coin1_name} Price', color='blue')
    plt.plot(df.index, df['price_coin2'], label=f'{coin2_name} Price', color='green')
    plt.title(f'{coin1_name} and {coin2_name} Prices')
    plt.xlabel('Date')
    plt.ylabel('Price')
    plt.legend()

    # B) Plot the spread
    plt.subplot(3, 1, 2)
    plt.plot(df.index, df['Spread'], label='Spread', color='purple')
    plt.axhline(median_spread, color='red', linestyle='--', label='Median')
    plt.title('Spread Between Coin Prices')
    plt.xlabel('Date')
    plt.ylabel('Spread')
    plt.legend()

    # C) Plot residuals
    plt.subplot(3, 1, 3)
    plt.plot(df.index, residuals, label='Residuals', color='orange')
    plt.axhline(0, color='red', linestyle='--', label='Mean')
    plt.title('Residuals of the Linear Regression')
    plt.xlabel('Date')
    plt.ylabel('Residuals')
    plt.legend()

    plt.tight_layout()
    plt.show()


@rerunnable
def asset_balancer():
    def divide_assets(asset1, asset2, total):
        asset1_amount = total * (asset1 / (asset1 + asset2))
        asset2_amount = total * (asset2 / (asset1 + asset2))
        print(f'{asset1_name}: {asset1_amount:.4f}, {asset2_name}: {asset2_amount:.4f}')

    def divide_assets_per_ext_coin(asset1, asset2, total, asset1_rate, asset2_rate):
        asset1_amount = (total * asset1_rate) * (asset1 / (asset1 + asset2))
        asset2_amount = (total * asset2_rate) * (asset2 / (asset1 + asset2))
        print(f'{asset1_name}: {asset1_amount:.4f},{asset2_name}: {asset2_amount:.4f}')

    asset1_name = input('Provide name of asset 1: ').strip().upper()
    asset2_name = input('Provide name of asset 2: ').strip().upper()
    asset1 = float(input('Provide asset 1 value in LP: ').replace(',', '.'))
    asset2 = float(input('Provide asset 2 value in LP: ').replace(',', '.'))
    amount_to_distribute = float(input('Provide total value to divide: ').replace(',', '.'))

    print("Is divided value denominated in different to result's coin (e.g., ETH -> cbETH, WETH)?")
    choice = input('Provide y/n: ')

    if choice == 'y':
        asset1_rate = float(
            input(f'Provide exchange rate for 100 {asset1_name} / 100 {asset2_name} (e.g., look at Jumper): ').replace(
                ',', '.')) / 100
        asset2_rate = 1 / asset1_rate

        divide_assets_per_ext_coin(asset1, asset2, amount_to_distribute, asset1_rate, asset2_rate)

    else:
        divide_assets(asset1, asset2, amount_to_distribute)


@rerunnable
def log_current_lp_notionals():
    """
    Log current LP notionals for an existing pair, with an option to calculate and plot impermanent loss.
    """
    positions = load_positions()
    if not positions:
        print("❌ No positions available.")
        return

    # Display options to the user
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("📝  LOG CURRENT LP NOTIONALS  📝")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("1. Add new notionals entry")
    print("2. Delete old notionals entry")

    choice = input("\nSelect an option (1 or 2): ").strip()
    if choice == '1':
        # Proceed to add new notionals entry

        # Create a map of positions by pair
        position_map = {}
        for position in positions:
            position_map[position['pair']] = position  # Assuming one position per pair

        # Display available pairs
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("🔹  SELECT A PAIR TO LOG NOTIONALS  🔹")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        for idx, pair in enumerate(position_map.keys(), 1):
            print(f"{idx}. {pair}")

        selected_idx = int(get_input("Select a pair by number: ", '0'))
        pairs = list(position_map.keys())
        if selected_idx < 1 or selected_idx > len(pairs):
            print("❌ Invalid selection.")
            return

        selected_pair = pairs[selected_idx - 1]
        coin1_name, coin2_name = selected_pair.split('-')
        coin1_id = position_map[selected_pair]['coingecko_id_coin1']
        coin2_id = position_map[selected_pair]['coingecko_id_coin2']

        # Prompt user for current quantities
        quantity_1 = float(get_input(f"Enter current Quantity of {coin1_name}: ", '0').replace(',', '.'))
        quantity_2 = float(get_input(f"Enter current Quantity of {coin2_name}: ", '0').replace(',', '.'))

        # Prompt user for current APR
        current_apr = float(get_input("Enter current APR (%): ", '0').replace(',', '.'))

        # Fetch latest prices
        price_coin1 = get_latest_price(coin1_id)
        price_coin2 = get_latest_price(coin2_id)

        if price_coin1 is None or price_coin2 is None:
            print("Failed to fetch prices. Please try again.")
            return

        # Calculate current LP valuation
        valuation = quantity_1 * price_coin1 + quantity_2 * price_coin2
        proportion = quantity_1 * price_coin1 / valuation

        # Load existing LP notionals
        lp_notionals = load_lp_notionals()

        # Append new data
        lp_notionals.append({
            'pair': selected_pair,
            'date': datetime.now(),
            'quantity_1': quantity_1,
            'quantity_2': quantity_2,
            'valuation': valuation,
            'proportion': proportion,
            'apr': current_apr
        })

        # Save updated LP notionals
        save_lp_notionals(lp_notionals)

        # Filter data for the selected pair
        pair_data = [entry for entry in lp_notionals if entry['pair'] == selected_pair]

        # Prepare data for plotting
        dates = [entry['date'] for entry in pair_data]
        quantities_1 = [entry['quantity_1'] for entry in pair_data]
        quantities_2 = [entry['quantity_2'] for entry in pair_data]
        valuations = [entry['valuation'] for entry in pair_data]
        aprs = [entry['apr'] for entry in pair_data]

        # Plot quantities and total valuation
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))

        # Plot quantities of both coins
        ax1.plot(dates, quantities_1, label=f'{coin1_name} Quantity', color='blue', marker='o')
        ax1.plot(dates, quantities_2, label=f'{coin2_name} Quantity', color='green', marker='o')
        ax1.set_xlabel('Date')
        ax1.set_ylabel('Quantities')
        ax1.legend(loc='upper left')
        ax1.set_title(f'Quantities of {coin1_name} and {coin2_name} Over Time')
        ax1.grid(True)

        # Format x-axis dates
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.setp(ax1.get_xticklabels(), rotation=45, ha='right')

        # Plot total valuation and APR
        ax2.plot(dates, valuations, label='Total Valuation (USD)', color='red', marker='o')
        ax2.set_xlabel('Date')
        ax2.set_ylabel('Valuation (USD)', color='red')
        ax2.tick_params(axis='y', labelcolor='red')
        ax2.legend(loc='upper left')
        ax2.grid(True)

        # Create a twin axis to plot APR
        ax3 = ax2.twinx()
        ax3.plot(dates, aprs, label='APR (%)', color='purple', marker='x')
        ax3.set_ylabel('APR (%)', color='purple')
        ax3.tick_params(axis='y', labelcolor='purple')
        ax3.legend(loc='upper right')

        # Format x-axis dates
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.setp(ax2.get_xticklabels(), rotation=45, ha='right')

        plt.tight_layout()
        plt.show()

        # Call impermanent loss calculation function
        calculate_impermanent_loss_for_pair(selected_pair, lp_notionals)

    elif choice == '2':
        # Proceed to delete old notionals entry
        # Load existing LP notionals
        lp_notionals = load_lp_notionals()
        if not lp_notionals:
            print("❌ No LP notionals entries to delete.")
            return

        # List all entries
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("🗑️  DELETE LP NOTIONALS ENTRY  🗑️")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        for idx, entry in enumerate(lp_notionals, 1):
            date_str = entry['date'].strftime("%Y-%m-%d %H:%M")
            print(f"{idx}. 📅 Date: {date_str}, 🔹 Pair: {entry['pair']}, 💰 Valuation: {entry['valuation']:.2f} USD")

        # Prompt user to select entry to delete
        selected_idx = int(get_input("Select an entry to delete by number: ", '0'))
        if selected_idx < 1 or selected_idx > len(lp_notionals):
            print("❌ Invalid selection.")
            return

        # Confirm deletion
        confirm = get_input(f"Are you sure you want to delete entry {selected_idx}? (y/n): ", 'n').lower()
        if confirm == 'y':
            deleted_entry = lp_notionals.pop(selected_idx - 1)
            save_lp_notionals(lp_notionals)
            print(f"\n✅ Entry for pair {deleted_entry['pair']} on {deleted_entry['date']} has been deleted.")
        else:
            print("❌ Deletion cancelled.")

    else:
        print("❌ Invalid selection.")
        return


def calculate_impermanent_loss_for_pair(selected_pair, balance_movements):
    """
    Calculates impermanent loss for a specific pair starting from the 'Open LP' entry.
    """
    # Filter the data for the selected pair and the type 'open lp'
    pair_data = [entry for entry in balance_movements if entry['pair'] == selected_pair]

    # Find the initial "Open LP" entry
    try:
        initial_entry = next((entry for entry in pair_data if entry['type'] == 'open lp'), None)
    except KeyError as e:
        return print(f"Exception: There is no Open LP entry for {selected_pair}",color="red")


    if not initial_entry:
        print("❌ No 'Open LP' entry found for this pair.")
        return

    # Find the latest entry for comparison
    latest_entry = pair_data[-1]

    # Ensure the latest entry is not the same as the initial entry (no impermanent loss if they are the same)
    if initial_entry == latest_entry:
        print("❌ Not enough data after the 'Open LP' entry to calculate impermanent loss.")
        return

    # Extract initial and current total valuations
    initial_value_usd = (
            initial_entry['lp_balances'][selected_pair.split('-')[0]] * get_latest_price(
        initial_entry['pair'].split('-')[0]) +
            initial_entry['lp_balances'][selected_pair.split('-')[1]] * get_latest_price(
        initial_entry['pair'].split('-')[1])
    )
    current_value_usd = (
            latest_entry['lp_balances'][selected_pair.split('-')[0]] * get_latest_price(
        latest_entry['pair'].split('-')[0]) +
            latest_entry['lp_balances'][selected_pair.split('-')[1]] * get_latest_price(
        latest_entry['pair'].split('-')[1])
    )

    # Calculate impermanent loss
    impermanent_loss_usd = initial_value_usd - current_value_usd
    impermanent_loss_percentage = (impermanent_loss_usd / initial_value_usd) * 100

    print("\n--- Impermanent Loss Calculation ---")
    print(f"Initial Total Value (USD): ${initial_value_usd:.2f}")
    print(f"Current Total Value (USD): ${current_value_usd:.2f}")
    print(f"Impermanent Loss: ${impermanent_loss_usd:.2f}")
    print(f"Impermanent Loss Percentage: {impermanent_loss_percentage:.2f}%")

    # Plot the impermanent loss over time
    plot_impermanent_loss(pair_data, initial_entry)


def plot_impermanent_loss(pair_data, initial_entry):
    """
    Plots the impermanent loss over time starting from the 'Open LP' entry.
    """
    # Filter data starting from the 'Open LP' entry
    start_index = pair_data.index(initial_entry)
    relevant_data = pair_data[start_index:]

    dates = [entry['date'] for entry in relevant_data]
    valuations = [
        entry['lp_balances'][entry['pair'].split('-')[0]] * get_latest_price(entry['pair'].split('-')[0]) +
        entry['lp_balances'][entry['pair'].split('-')[1]] * get_latest_price(entry['pair'].split('-')[1])
        for entry in relevant_data
    ]
    initial_value = valuations[0]
    impermanent_losses = [(initial_value - valuation) / initial_value * 100 for valuation in valuations]

    plt.figure(figsize=(10, 6))
    plt.plot(dates, impermanent_losses, marker='o', linestyle='-', color='b')
    plt.title(f"Impermanent Loss Over Time for {initial_entry['pair']} (Starting from 'Open LP')")
    plt.xlabel("Date")
    plt.ylabel("Impermanent Loss (%)")
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()


@rerunnable
def mini_functions():
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("🪄    MINI FUNCTIONS   🪄")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("1. Get Coingecko Id")
    print("2. Check Coingecko Price")
    print("3. Plot prices asset1/asset2")
    print("4. Calculate loan vs current position discrepancy")
    print("5. Calculate cointegration")
    print("6. Log current LP notionals")
    print("7. Calculate New LP ratios")

    choice = input("\nSelect an option: ").strip()
    if choice == '1':
        coin_name = get_input("Provide coin name: ", '')
        coingecko_id = get_coin_id(coin_name)
        print(f"Coingecko id is: {coingecko_id}")
    elif choice == '2':
        coin_name = get_input("Provide coin name: ", '')
        coingecko_id = get_coin_id(coin_name)
        print(f"Price of {coin_name} is:   {get_latest_price(coingecko_id)} ")

    elif choice == '3':
        analyze_pair_performance()
    elif choice == '4':
        calculate_loan_vs_position_discrepancy()
    elif choice == '5':
        calculate_cointegration()
    elif choice == '6':
        log_current_lp_notionals()
    elif choice == '7':
        asset_balancer()
    else:
        print("❌ Invalid choice. Please try again.")


# Main menu with all functionalities intact and "Book Rebalancing" option added
def main():
    while True:
        print('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
        print("                   📋  OPTIONS MENU  📋 ")
        print('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
        print("1. View Positions")
        print("2. Calculate Overall APY", color="blue")
        print("3. Increase/Decrease Position")
        print("4. Modify Last Entry")
        print("5. Add New Pair")
        print("6. Delete Position(s)")
        print("7. Book a Fee", color ="green")
        print("8. Book Rebalancing")
        print("9. Mini Functions")
        print("10.Exit")
        print('\n', 2 * '- - - - - - - - - - - - ', '\n')
        choice = input("Select an option: ", 'blue').strip()

        if choice == '1':
            view_positions()
        elif choice == '2':
            calculate_overall_apy()
        elif choice == '3':
            modify_position()
        elif choice == '4':
            modify_last_entry()
        elif choice == '5':
            create_new_position()
        elif choice == '6':
            delete_position()
        elif choice == '7':
            book_fee()
        elif choice == '8':
            book_rebalancing()
        elif choice == '9':
            mini_functions()
        elif choice == '10':
            sys.exit(0)
        else:
            print("❌ Invalid choice. Please try again.",color = "red")


if __name__ == "__main__":
    while True:
        main()