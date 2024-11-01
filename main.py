import pickle
import datetime
import os
import matplotlib.pyplot as plt
from collections import defaultdict

# Paths to store the positions and rebalancing entries
DATA_FILE = 'liquidity_positions.pkl'
REBALANCE_FILE = 'balance_movements.pkl'


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


# Helper function to handle default inputs (auto-d
def get_input(prompt, default_value):
    user_input = input(prompt).strip()

    # If input is empty, return the default value
    if user_input == '':
        return default_value

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
        return user_input


# Function to book a new fee
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
    fee_date = datetime.datetime.now().date()

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
def book_rebalancing():
    positions = load_positions()
    if not positions:
        print("❌ No positions available to book rebalancing.")
        return

    # Create a map of positions by pair
    position_map = {}
    for position in positions:
        position_map[position['pair']] = position  # Assuming one position per pair

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
        # Proceed to add a new rebalancing
        coin1_name, coin2_name = selected_pair.split('-')

        # Get metamask balances
        metamask_balance_coin1 = float(get_input(f"Enter Metamask balance for {coin1_name}: ", '0').replace(',', '.'))
        metamask_balance_coin2 = float(get_input(f"Enter Metamask balance for {coin2_name}: ", '0').replace(',', '.'))

        # Get LP balances
        lp_balance_coin1 = float(get_input(f"Enter LP balance for {coin1_name}: ", '0').replace(',', '.'))
        lp_balance_coin2 = float(get_input(f"Enter LP balance for {coin2_name}: ", '0').replace(',', '.'))

        # Get the type of transaction
        print("Select the type of transaction:")
        print("1. Initial")
        print("2. Open LP")
        print("3. Redemption")
        type_dict = {'1': 'initial', '2': 'open lp', '3': 'redemption'}
        type_choice = get_input("Enter the number corresponding to the type: ", '1')
        transaction_type = type_dict.get(type_choice, 'initial')

        # If it's an "Open LP", ask for min and max prices
        if transaction_type == 'open lp':
            min_price = float(get_input(f"Enter the minimum price for {selected_pair}: ", '0').replace(',', '.'))
            max_price = float(get_input(f"Enter the maximum price for {selected_pair}: ", '0').replace(',', '.'))
        else:
            min_price = max_price = None

        # Ask for the date and hour of rebalancing (no minutes)
        date_str = get_input("Enter the date of rebalancing (YYYY-MM-DD): ",
                             datetime.datetime.now().strftime("%Y-%m-%d"))
        hour_str = get_input("Enter the hour of rebalancing (HH): ", datetime.datetime.now().strftime("%H"))
        rebalance_datetime = datetime.datetime.strptime(f"{date_str} {hour_str}", "%Y-%m-%d %H")

        # Save the entry into balance movements
        balance_movements = load_balance_movements()
        balance_entry = {
            'pair': selected_pair,
            'metamask_balances': {
                coin1_name: metamask_balance_coin1,
                coin2_name: metamask_balance_coin2
            },
            'lp_balances': {
                coin1_name: lp_balance_coin1,
                coin2_name: lp_balance_coin2
            },
            'type': transaction_type,
            'min_price': min_price,
            'max_price': max_price,
            'date': rebalance_datetime
        }
        balance_movements.append(balance_entry)
        save_balance_movements(balance_movements)

        print("\n✅ Rebalancing booked successfully.")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    elif action == "d":
        # Proceed to delete an existing rebalancing
        delete_rebalancing()


# Function to create a new position
def create_new_position():
    pair = get_input("Enter Coin Pair (e.g., USDT-USD+): ", '')
    coin1_name, coin2_name = pair.split('-')

    quantity_1 = float(get_input(f"Enter Quantity of {coin1_name}: ", '0'))
    quantity_2 = float(get_input(f"Enter Quantity of {coin2_name}: ", '0'))

    date_input = get_input("Enter Date Added (YYYY-MM-DD) or press Enter for today: ", '')
    date_added = datetime.datetime.strptime(date_input, "%Y-%m-%d") if date_input else datetime.datetime.now()

    positions = load_positions()

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
        'fees': []  # Store manually added fees here
    }

    positions.append(new_position)
    save_positions(positions)


# Function to calculate overall APY and summarize fees
def calculate_overall_apy():
    positions = load_positions()
    if not positions:
        print("❌ No positions available to calculate overall APY.")
        return

    position_map = {}
    for position in positions:
        position_map.setdefault(position['pair'], []).append(position)

    total_weighted_apr = 0
    total_investment_all = 0

    for pair, pos_list in position_map.items():

        temp_pair_name = ''
        print(f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"📊  SUMMARY FOR PAIR: {pair}  📊")
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        total_fee_coin1 = sum(pos['total_fee_coin1'] for pos in pos_list)
        total_fee_coin2 = sum(pos['total_fee_coin2'] for pos in pos_list)
        total_lp_bonus = sum(pos['lp_provider_bonus'] for pos in pos_list)
        total_investor_paid_fees = sum(pos['investor_paid_fees'] for pos in pos_list)

        # Combine fees from both created positions and manually booked fees
        total_manual_fees = sum(fee['amount'] for pos in pos_list for fee in pos.get('fees', []))

        current_prices = {
            'coin1': float(get_input(f"Enter current price for {pair.split('-')[0]}: ", '0')),
            'coin2': float(get_input(f"Enter current price for {pair.split('-')[1]}: ", '0')),
            'bonus_coin': float(get_input("Enter current price for bonus coin: ", '0'))
        }

        net_quantity_1 = sum(pos['initial_quantity_1'] for pos in pos_list)
        net_quantity_2 = sum(pos['initial_quantity_2'] for pos in pos_list)

        total_investment = net_quantity_1 * current_prices['coin1'] + net_quantity_2 * current_prices['coin2']

        earliest_date_added = min(pos['date_added'] for pos in pos_list)
        days_active = (datetime.datetime.now() - earliest_date_added).days + 1

        # Include manual fees in the fee calculation
        total_fees = ((total_fee_coin1 * current_prices['coin1'] +
                       total_fee_coin2 * current_prices['coin2'] +
                       total_lp_bonus * current_prices['bonus_coin']) - total_investor_paid_fees - total_manual_fees)

        positive_gain_usdt = (total_fee_coin1 * current_prices['coin1']) + \
                             (total_fee_coin2 * current_prices['coin2']) + \
                             (total_lp_bonus * current_prices['bonus_coin'])

        if total_investment > 0 and days_active > 0:
            apr = (total_fees / total_investment) * (365 / days_active) * 100
        else:
            apr = 0

        print(f"✔️ Total Fee for {pair.split('-')[0]}: {total_fee_coin1:.2f}")
        print(f"✔️ Total Fee for {pair.split('-')[1]}: {total_fee_coin2:.2f}")
        print(f"✔️ LP Provider Bonus: {total_lp_bonus:.2f}")
        print(f"✔️ Positive Gain (USDT): {positive_gain_usdt:.2f}")
        print(f"✔️ Investor Paid Fees (USDT): {total_investor_paid_fees + total_manual_fees:.2f}")
        print(f"✔️ Average Investment Notional: {total_investment:.2f}")
        print(f"✔️ APY for {pair}: {apr:.2f}%")

        total_weighted_apr += apr * total_investment
        total_investment_all += total_investment

    if total_investment_all > 0:
        overall_apr = total_weighted_apr / total_investment_all
        print(f"\nThe overall APY for all positions is: {overall_apr:.2f}%\n")

    else:
        print("❌ No active positions to calculate APY.")


# Function to view positions and plot price persistence chart (based on hours)
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
        print(f"\nPair: {pair}")
        total_quantity_1 = sum(pos['initial_quantity_1'] for pos in pos_list)
        total_quantity_2 = sum(pos['initial_quantity_2'] for pos in pos_list)
        total_fee_coin1 = sum(pos['total_fee_coin1'] for pos in pos_list)
        total_fee_coin2 = sum(pos['total_fee_coin2'] for pos in pos_list)
        total_lp_bonus = sum(pos['lp_provider_bonus'] for pos in pos_list)
        total_investor_paid_fees = sum(pos['investor_paid_fees'] for pos in pos_list)

        # Combine fees from both created positions and manually booked fees
        total_manual_fees = sum(fee['amount'] for pos in pos_list for fee in pos.get('fees', []))

        # Display position data
        for position in pos_list:
            total_fees = position['investor_paid_fees'] + total_manual_fees
            print(f"📌 Date Added {position['date_added']}, "
                  f"Quantity 1: {position['initial_quantity_1']:.2f}, "
                  f"Quantity 2: {position['initial_quantity_2']:.2f}, "
                  f"Fee {pair.split('-')[0]}: {position['total_fee_coin1']:.2f}, "
                  f"Fee {pair.split('-')[1]}: {position['total_fee_coin2']:.2f}, "
                  f"LP Provider Bonus: {position['lp_provider_bonus']}, "


                  f"Investor Paid Fees: {total_fees:.2f}")

        # Display fees section with manual entries
        print(f"\n💸  FEE DEDUCTED FOR {pair}  💸")
        for position in pos_list:
            for fee in position.get('fees', []):
                print(f"Amount: {fee['amount']}, Description: {fee['description']}, Date: {fee['date']}\n")
        print("")
        print(f"✔️ Total Quantity of {pair.split('-')[0]}: {total_quantity_1:.2f}")
        print(f"✔️ Total Quantity of {pair.split('-')[1]}: {total_quantity_2:.2f}")
        print(f"✔️ Total Manual Fees: {total_manual_fees:.2f}")
        print(f"✔️ Total Investor Paid Fees: {total_investor_paid_fees + total_manual_fees:.2f}")
        print(f"✔️ Total LP Provider Bonus: {total_lp_bonus}")
        if pair_iterator < position_list_len:
            print('\n             ━━━━━━━━━━━━━━━━━━━━━━━')

    # Display balance movements summary
    if balance_movements:
        temp_pair_name = ''
        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("          🔄  BALANCE MOVEMENTS SUMMARY  🔄")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        for entry in balance_movements:
            if {entry['pair']} != temp_pair_name and temp_pair_name != '':
                print("\n             ━━━━━━━━━━━━━━━━━━━━━━━")
            temp_pair_name = {entry['pair']}
            coin1_name, coin2_name = entry['pair'].split('-')
            print(f"\n📅 Date: {entry['date']}")
            print(f"🔹 Pair: {entry['pair']}")
            print(f"🔸 Type: {entry['type'].capitalize()}")
            print(f"💼 Metamask Balances: {coin1_name}: {entry['metamask_balances'][coin1_name]}, "
                  f"{coin2_name}: {entry['metamask_balances'][coin2_name]}")
            print(f"🏦 LP Balances: {coin1_name}: {entry['lp_balances'][coin1_name]}, "
                  f"{coin2_name}: {entry['lp_balances'][coin2_name]}")

    else:
        print("\n❌ No balance movements recorded.")


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

    # Handle empty input for investor_paid_fees
    new_investor_paid_fees = get_input(
        f"Enter new Investor Paid Fees (or press Enter to keep {last_position['investor_paid_fees']}): ", "")
    if new_investor_paid_fees:
        last_position['investor_paid_fees'] = float(new_investor_paid_fees)

    save_positions(positions)
    print("\n✅ Last entry modified successfully.")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


# Function to modify an existing position
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
def delete_all_positions():
    confirm = get_input(f"❓ Are you sure you want to delete all positions? (y/n): ", 'n').lower()
    if confirm == 'y':
        if os.path.exists(DATA_FILE):
            os.remove(DATA_FILE)
            print("\n✅ All positions have been deleted.")
        else:
            print("❌ No positions to delete.")
    else:
        print("❌ Deletion cancelled.")


# Function to delete a position or all positions
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


# Main menu with all functionalities intact and "Book Rebalancing" option added
def main():
    while True:
        print('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
        print("                   📋  OPTIONS MENU  📋 ")
        print('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
        print("1. View Positions")
        print("2. Calculate Overall APY")
        print("3. Increase/Decrease Position")
        print("4. Modify Last Entry")
        print("5. Add New Pair")
        print("6. Delete Position(s)")
        print("7. Book a Fee")
        print("8. Book Rebalancing")
        print("9. Exit")
        print('\n', 2 * '- - - - - - - - - - - - ', '\n')
        choice = input("Select an option: ").strip()

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
            print("Exiting.")
            break
        else:
            print("❌ Invalid choice. Please try again.")


if __name__ == "__main__":
    main()