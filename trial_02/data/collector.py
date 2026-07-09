import socket
import time
import re
import csv
from datetime import datetime
from tqdm import tqdm
import sys

class LibreVNA_SCPI:
    def __init__(self, host='127.0.0.1', port=19542): # Update port as needed
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(15.0) # Increased timeout to prevent drops
        self.sock.connect((self.host, self.port))

    def send_cmd(self, cmd):
        self.sock.sendall(f"{cmd}\n".encode('utf-8'))

    def query_cmd(self, cmd):
        self.sock.sendall(f"{cmd}\n".encode('utf-8'))
        response = b""
        while True:
            chunk = self.sock.recv(4096)
            response += chunk
            if b'\n' in chunk:
                break
        return response.decode('utf-8').strip()

    def configure_sweep(self, start_hz, stop_hz, points, if_bw_hz, averages):
        self.send_cmd("DEV:MODE VNA")
        self.send_cmd("VNA:SWEEP FREQUENCY")
        self.send_cmd(f"VNA:FREQ:START {start_hz}")
        self.send_cmd(f"VNA:FREQ:STOP {stop_hz}")
        self.send_cmd(f"VNA:ACQ:POINTS {points}")
        self.send_cmd(f"VNA:ACQ:IFBW {if_bw_hz}")
        self.send_cmd(f"VNA:ACQ:AVG {averages}")
        
        # Configure traces for S11 and S22
        self.send_cmd("VNA:TRAC:PARAM S11, S11")
        self.send_cmd("VNA:TRAC:PARAM S22, S22")

    def get_dual_trace_data(self):
        """Triggers a single sweep and fetches both S11 and S22."""
        self.send_cmd("VNA:ACQ:SINGLE TRUE")
        
        # Wait for the sweep/averaging to finish
        while True:
            finished = self.query_cmd("VNA:ACQ:FINished?")
            if finished.upper() == "TRUE":
                break
            time.sleep(0.05) # Brief sleep to prevent spamming the socket

        # Retrieve the data
        raw_s11 = self.query_cmd("VNA:TRAC:DATA? S11")
        raw_s22 = self.query_cmd("VNA:TRAC:DATA? S22")
        
        s11_parsed = self._parse_trace_data(raw_s11)
        s22_parsed = self._parse_trace_data(raw_s22)

        # Ensure data alignment
        if len(s11_parsed) != len(s22_parsed):
            raise ValueError("S11 and S22 data length mismatch!")

        # Combine data
        combined_data = []
        for p11, p22 in zip(s11_parsed, s22_parsed):
            combined_data.append({
                "frequency_hz": p11["frequency_hz"],
                "s11_real": p11["real"],
                "s11_imag": p11["imaginary"],
                "s22_real": p22["real"],
                "s22_imag": p22["imaginary"]
            })
            
        return combined_data

    def _parse_trace_data(self, raw_data):
        parsed_data = []
        tuples = re.findall(r'\[(.*?)\]', raw_data)
        for t in tuples:
            parts = t.split(',')
            if len(parts) == 3:
                parsed_data.append({
                    "frequency_hz": float(parts[0]),
                    "real": float(parts[1]),
                    "imaginary": float(parts[2])
                })
        return parsed_data

    def close(self):
        self.send_cmd("DEV:DISC")
        self.sock.close()

def main():
    # --- Configuration ---
    HOST = '127.0.0.1'
    PORT = 19542            # Check LibreVNA-GUI preferences for exact port
    DURATION_MINUTES = 10
    DURATION_SECONDS = DURATION_MINUTES * 60
    
    # Sweep parameters balanced for speed vs granularity
    START_FREQ = 1_000_000      # 1 MHz
    STOP_FREQ = 6_000_000_000   # 6 GHz
    POINTS = 1001               # Good spectrum granularity
    IFBW = 1000                 # 1 kHz IFBW allows for faster sweep times
    AVERAGES = 1                # 1 average captures raw temporal changes better
    
    # File setup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"headspace_data_{timestamp}.csv"
    
    print("\n--- LibreVNA Headspace Data Collector ---")
    print(f"Target file: {filename}")
    print(f"Duration:    {DURATION_MINUTES} minutes")
    print(f"Sweep Setup: {START_FREQ/1e6} MHz to {STOP_FREQ/1e9} GHz, {POINTS} points")
    
    try:
        vna = LibreVNA_SCPI(host=HOST, port=PORT)
    except ConnectionRefusedError:
        print(f"\n[!] Error: Could not connect to LibreVNA at {HOST}:{PORT}")
        print("Please ensure LibreVNA-GUI is open and the SCPI server is enabled.")
        sys.exit(1)

    print("\nConfiguring VNA... ", end="")
    vna.configure_sweep(start_hz=START_FREQ, 
                        stop_hz=STOP_FREQ, 
                        points=POINTS, 
                        if_bw_hz=IFBW, 
                        averages=AVERAGES)
    print("Done.")

    # Await user readiness
    input("\nPress [ENTER] when you are ready to begin collecting data...")

    # Open CSV and begin logging
    try:
        with open(filename, mode='w', newline='') as csv_file:
            fieldnames = ['Timestamp', 'Frequency_Hz', 'S11_Real', 'S11_Imag', 'S22_Real', 'S22_Imag']
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()

            start_time = time.time()
            sweep_count = 0

            # tqdm progress bar tracking elapsed time
            with tqdm(total=DURATION_SECONDS, desc="Collecting", unit="s", bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}s [Sweeps: {postfix}]") as pbar:
                while True:
                    current_time = time.time()
                    elapsed = current_time - start_time
                    
                    if elapsed >= DURATION_SECONDS:
                        pbar.n = DURATION_SECONDS
                        pbar.refresh()
                        break

                    # Fetch data
                    dual_data = vna.get_dual_trace_data()
                    timestamp_str = datetime.now().isoformat()

                    # Write to CSV
                    for pt in dual_data:
                        writer.writerow({
                            'Timestamp': timestamp_str,
                            'Frequency_Hz': pt['frequency_hz'],
                            'S11_Real': pt['s11_real'],
                            'S11_Imag': pt['s11_imag'],
                            'S22_Real': pt['s22_real'],
                            'S22_Imag': pt['s22_imag']
                        })
                    
                    # Ensure data is saved incrementally in case of crash
                    csv_file.flush() 
                    sweep_count += 1
                    
                    # Update progress bar
                    pbar.n = min(elapsed, DURATION_SECONDS)
                    pbar.set_postfix_str(str(sweep_count))
                    pbar.refresh()

    except KeyboardInterrupt:
        print("\n\nCollection aborted by user. Data saved up to this point.")
    except Exception as e:
        print(f"\n\nAn error occurred: {e}")
    finally:
        vna.close()
        print(f"\nCollection complete! Data saved to {filename}")

if __name__ == "__main__":
    main()