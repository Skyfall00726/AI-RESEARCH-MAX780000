#!/usr/bin/env python3
"""
Simple Keithley current monitor to debug MAX78000 power issues
"""

import pyvisa
import time

def monitor_current():
    """Monitor current draw from MAX78000"""
    
    try:
        # Create resource manager with pyvisa-py backend
        rm = pyvisa.ResourceManager('@py')
        
        # Try to find Keithley (you may need to adjust this address)
        resources = rm.list_resources()
        print(f"Available resources: {resources}")
        
        # Common Keithley addresses to try
        addresses_to_try = [
            "USB0::0x05E6::0x2450::04390796::INSTR",
            "USB0::0x05E6::0x2450::*::INSTR",
        ]
        
        keithley = None
        for addr in addresses_to_try:
            try:
                print(f"Trying address: {addr}")
                keithley = rm.open_resource(addr)
                keithley.timeout = 5000
                idn = keithley.query("*IDN?")
                print(f"Connected to: {idn.strip()}")
                break
            except Exception as e:
                print(f"Failed to connect to {addr}: {e}")
                continue
        
        if keithley is None:
            print("Could not connect to Keithley. Manual check needed.")
            print("\nManual Check Instructions:")
            print("1. Look at Keithley 2450 display")
            print("2. Check if OUTPUT is ON (should show green)")
            print("3. Look at current reading - should show some mA if MAX78000 is drawing power")
            print("4. If current is 0.000 mA, MAX78000 isn't getting power properly")
            return
            
        # Configure for voltage source, current measure
        keithley.write("*RST")
        keithley.write("smu.source.func = smu.FUNC_DC_VOLTAGE")
        keithley.write("smu.source.level = 5.0")
        keithley.write("smu.measure.func = smu.FUNC_DC_CURRENT")
        keithley.write("smu.source.output = smu.ON")
        
        print("\nMonitoring current draw (press Ctrl+C to stop):")
        print("Time\t\tVoltage(V)\tCurrent(mA)")
        print("-" * 40)
        
        while True:
            voltage = float(keithley.query("print(smu.measure.voltage())"))
            current = float(keithley.query("print(smu.measure.current())"))
            current_ma = current * 1000  # Convert to mA
            
            timestamp = time.strftime("%H:%M:%S")
            print(f"{timestamp}\t{voltage:.3f}V\t\t{current_ma:.1f}mA")
            
            if current_ma < 1:
                print("WARNING: Very low current draw - MAX78000 may not be powered properly")
            elif current_ma > 10:
                print("INFO: Normal current draw detected")
                
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\nMonitoring stopped")
        if keithley:
            keithley.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    monitor_current()
