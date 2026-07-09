# -*- coding: utf-8 -*-
# File: vna_datalogger.py
# Description: A script to log data from a VNA at specified intervals and steps.

import pyvisa as visa
import sys
import csv
import os
import time
from datetime import datetime
from tqdm import tqdm

# --- User Configuration ---
# TODO: Set your VNA's VISA address here
VISA_ADDRESS = 'TCPIP0::A-N5231A-11062::inst0::INSTR'
VISA_ADDRESS = 'TCPIP0::169.254.82.72::inst0::INSTR'
VNA_WINDOW = 1

def get_user_settings():
    """Prompts the user for all necessary data logging settings."""
    print("\n--- Datalogger Configuration ---")
    
    gas_name = input("Enter the gas name (e.g., MeOH): ")
    
    # Get step type (ppm or uL)
    unit = ""
    while unit not in ['ppm', 'ul']:
        unit = input("Step in 'ppm' or 'uL'? ").lower()
        if unit == 'μl': # Handle micro-liter symbol
            unit = 'ul'

    # Get numerical inputs with error handling
    try:
        step_value = float(input(f"Enter the {unit} step value: "))
        initial_value = float(input(f"Enter the initial {unit} value: "))
        final_value = float(input(f"Enter the final {unit} value to stop at: "))
        num_samples = int(input("Enter the number of samples per step: "))
        collection_interval = int(input("Enter the collection interval (in seconds): "))
    except ValueError:
        print("\n❌ ERROR: Invalid numerical input. Please enter numbers only.")
        sys.exit()

    # Create the main directory for the gas
    if not os.path.exists(gas_name):
        os.makedirs(gas_name)
        print(f"✅ Created directory: '{gas_name}'")

    return {
        "gas_name": gas_name,
        "unit": unit,
        "step_value": step_value,
        "current_value": initial_value,
        "final_value": final_value,
        "num_samples": num_samples,
        "collection_interval": collection_interval,
    }

def acquire_and_save_data(inst, settings, sample_num):
    """Acquires data from all active traces and saves it to CSV files."""
    try:
        # Get a list of all active trace numbers in the specified window
        catalog_str = inst.query(f"DISP:WIND{VNA_WINDOW}:CAT?").strip().replace('"', '')
        trace_numbers = [int(t) for t in catalog_str.split(',') if t]
        
        if not trace_numbers:
            print(f"⚠️  No active traces found in Window {VNA_WINDOW}. Skipping sample.")
            return

        # Generate a timestamp for the current acquisition
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Iterate through each trace and save its data
        for trace in trace_numbers:
            # Get the measurement name (e.g., S21, S11)
            meas_list = inst.query(f"CALC{trace}:PAR:CAT?").strip().replace('"', '').split(',')
            if not (meas_list and meas_list[0]):
                print(f"⚠️  No measurement found for Trace {trace}. Skipping.")
                continue
            
            meas_name = meas_list[0]
            
            # Select the measurement to make it active for data transfer
            inst.write(f"CALC{trace}:PAR:SEL '{meas_name}'")
            inst.query('*OPC?') # Wait for command to complete

            # Get Frequency (X-axis) and Measurement (Y-axis) data
            x_data = inst.query_binary_values(f"CALC{trace}:X?", datatype='f')
            y_data = inst.query_binary_values(f"CALC{trace}:DATA? FDATA", datatype='f')

            # --- File Saving ---
            # Construct a descriptive filename
            filename = (
                f"{settings['gas_name']}/"
                f"{settings['current_value']}{settings['unit']}_"
                f"{meas_name}_"
                f"{timestamp}_S{sample_num:04}.csv"
            )

            # Write data to the CSV file
            with open(filename, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['Frequency (Hz)', 'Measurement']) # Write header
                writer.writerows(zip(x_data, y_data))

    except Exception as e:
        print(f"\n❌ ERROR during data acquisition: {e}")


def main():
    """Main function to run the datalogger."""
    inst = None
    try:
        # --- 1. Get User Settings ---
        settings = get_user_settings()

        # --- 2. Establish VNA Connection ---
        print("\n--- VNA Connection ---")
        rm = visa.ResourceManager()
        inst = rm.open_resource(VISA_ADDRESS)
        inst.timeout = 25000  # Use a generous timeout
        
        # --- 3. Setup Instrument ---
        inst.write('*CLS')
        # Set byte order to match most PCs (Big Endian for REAL,64)
        inst.write('FORM:BORD SWAP') 
        # Set data transfer format to 64-bit float
        inst.write('FORM:DATA REAL') 
        
        idn_string = inst.query('*IDN?')
        print(f"✅ Connected to: {idn_string.strip()}")
        inst.query('*OPC?') # Wait for all setup commands to complete

        # --- 4. Main Data Collection Loop ---
        current_val = settings['current_value']
        while current_val <= settings['final_value']:
            current_val = round(current_val,1) # FIX: Weirdly large number of decimals...
            
            settings['current_value'] = current_val
            print("-" * 40)
            
            # Prompt user to continue
            ready = input(f"Ready to measure at {current_val} {settings['unit']}? (y/n): ").lower()
            if ready != 'y':
                print("Data collection paused. Press 'y' when ready to resume.")
                continue
            
            # Use tqdm for a progress bar during sample collection
            for i in tqdm(range(settings['num_samples']), desc=f"Sampling at {current_val}{settings['unit']}"):
                acquire_and_save_data(inst, settings, i + 1)
                # Wait for the specified interval before the next sample
                if i < settings['num_samples'] - 1:
                    time.sleep(settings['collection_interval'])
            
            print(f"✅ Data collection complete for {current_val} {settings['unit']}.")
            
            # Increment for the next step
            current_val += settings['step_value']

        print("\n--- All measurements complete. ---")

    except visa.errors.VisaIOError as e:
        print(f"\n❌ VISA ERROR: Could not connect or communicate with the instrument.")
        print(f"   Details: {e}")
        print("   - Check if the VISA_ADDRESS is correct.")
        print("   - Check if the instrument is on and connected to the network.")
    except KeyboardInterrupt:
        print("\n\n🛑 Data collection stopped by user. Exiting gracefully.")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
    finally:
        # --- 5. Cleanup ---
        if inst:
            inst.close()
            print("\nConnection to VNA closed.")
        print("Program finished.")


if __name__ == "__main__":
    main()
