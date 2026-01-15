# utils/build_nifty250_universe.py

import csv
import json

def read_nifty250_symbols(csv_file_path):
    """
    Read symbols from NIFTY 250 CSV.
    Assumes a column named 'Symbol' exists.
    """
    symbols = []
    with open(csv_file_path, newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            symbol = row.get("Symbol") or row.get("SYMBOL") or row.get("symbol")
            if symbol:
                symbols.append(symbol.strip().upper())
    return symbols


def load_upstox_instruments(json_file_path):
    """
    Load Upstox instrument master JSON.
    """
    with open(json_file_path, "r") as f:
        return json.load(f)


def map_to_instrument_keys(symbols, instruments):
    """
    Match symbols with instrument master to extract instrument_key.
    Only NSE equity (segment == 'NSE_EQ') is considered.
    """
    keys = []
    symbol_set = set(symbols)

    for inst in instruments:
        # Ensure uppercase comparison
        inst_symbol = inst.get("trading_symbol", "").upper()
        segment = inst.get("segment", "")
        if inst_symbol in symbol_set and segment == "NSE_EQ":
            key = inst.get("instrument_key")
            # Avoid duplicates
            if key and key not in keys:
                keys.append(key)

    return keys


if __name__ == "__main__":
    nifty_symbols = read_nifty250_symbols("data/nifty250.csv")
    print(f"Total NIFTY250 symbols loaded: {len(nifty_symbols)}")

    instruments = load_upstox_instruments("data/instruments.json")
    instrument_keys = map_to_instrument_keys(nifty_symbols, instruments)

    print(f"Mapped {len(instrument_keys)} NSE_EQ instrument keys for NIFTY250:")
    for key in instrument_keys:
        print(key)

    # Optionally save to a file
    with open("data/nifty250_keys.json", "w") as f:
        json.dump(instrument_keys, f, indent=2)

    print("Saved instrument keys to data/nifty250_keys.json")
