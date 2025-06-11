import lseg.data as ld
import time
import pandas as pd
import os

# Configuration
CSV_FILE_PATH = 'aapl_stock_price.csv'
INSTRUMENT_RIC = 'AAPL.O' # Refinitiv Instrument Code for Apple Inc.
UPDATE_INTERVAL_SECONDS = 5 # How often to update the CSV (e.g., every 5 seconds)

# --- Main Execution ---
def main():
    session = None
    pricing_stream = None

    try:
        print("Opening LSEG Data Platform session...")
        session = ld.open_session('platform.rdp')
        session.open()

        print("Session opened successfully! Initializing CSV...")

        pd.DataFrame(columns=['Timestamp', 'Instrument', 'Last Price']).to_csv(CSV_FILE_PATH, index=False, header=True)

        print(f"Opening pricing stream for {INSTRUMENT_RIC}...")
        pricing_stream = ld.open_pricing_stream(
            universe=[INSTRUMENT_RIC],
            fields=['BID', 'ASK', 'LAST', 'TRDPRC_1', 'TIMACT', 'GV5', 'NETCHNG_1', 'OPEN_PRC', 'HIGH_1', 'LOW_1'] # Added more fields for debugging
        )

        print(f"Polling {INSTRUMENT_RIC} every {UPDATE_INTERVAL_SECONDS} seconds to update {CSV_FILE_PATH}. Press Ctrl+C to stop.")

        while True:
            snapshot_df = pricing_stream.get_snapshot()

            if not snapshot_df.empty:
                ric = snapshot_df.index[0] # Get RIC from the DataFrame's index

                # Safely try to extract TRDPRC_1, then LAST
                price = None
                if 'TRDPRC_1' in snapshot_df.columns and pd.notna(snapshot_df['TRDPRC_1'].iloc[0]):
                    price = snapshot_df['TRDPRC_1'].iloc[0]
                elif 'LAST' in snapshot_df.columns and pd.notna(snapshot_df['LAST'].iloc[0]):
                    price = snapshot_df['LAST'].iloc[0]

                # Extract timestamp
                timestamp = pd.to_datetime(snapshot_df['TIMACT'].iloc[0]) if 'TIMACT' in snapshot_df.columns and pd.notna(snapshot_df['TIMACT'].iloc[0]) else pd.Timestamp.now()

                if price is not None:
                    output_df = pd.DataFrame({
                        'Timestamp': [timestamp],
                        'Instrument': [ric],
                        'Last Price': [price]
                    })
                    output_df.to_csv(CSV_FILE_PATH, index=False, header=True)
                    print(f"[{timestamp.strftime('%H:%M:%S')}] Updated {ric} to {price}")
                else:
                    # If price is None, log the entire snapshot data to see what fields ARE present
                    print(f"[{timestamp.strftime('%H:%M:%S')}] No valid price (TRDPRC_1 or LAST) found for {ric}. Full snapshot data: {snapshot_df.to_dict('records')}")
            else:
                print(f"[{pd.Timestamp.now().strftime('%H:%M:%S')}] Received empty snapshot for {INSTRUMENT_RIC}. No data yet or issue with instrument.")

            time.sleep(UPDATE_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        print("\nScript stopped by user.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if pricing_stream:
            pricing_stream.close()
            print("Pricing stream closed.")
        if session:
            session.close()
            print("LSEG Data Platform session closed.")

if __name__ == "__main__":
    main()