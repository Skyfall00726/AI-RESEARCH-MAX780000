#!/usr/bin/env python3
"""
Simple test script to verify Keithley 2450 connection
"""

import pyvisa
import time

def test_keithley_connection():
    """Test basic connection to Keithley 2450"""
    
    # Common Keithley 2450 address patterns to try
    POSSIBLE_ADDRESSES = [
        "USB0::0x05E6::0x2450::04390796::INSTR",  # Default format
        "USB0::0x05E6::0x2450::*::INSTR",         # Wildcard serial
        "USB::0x05E6::0x2450::*::INSTR",          # Alternative format
        "TCPIP0::192.168.1.100::inst0::INSTR",    # Ethernet (if configured)
    ]
    
    print("=" * 50)
    print("Keithley 2450 Connection Test")
    print("=" * 50)
    
    try:
        # Create resource manager with pyvisa-py backend
        rm = pyvisa.ResourceManager('@py')
        print(f"Available resources: {rm.list_resources()}")
        
        # Try to connect to Keithley
        print(f"Attempting to connect to: {KEITHLEY_ADDRESS}")
        keithley = rm.open_resource(KEITHLEY_ADDRESS)
        
        # Set timeout
        keithley.timeout = 10000  # 10 seconds
        
        # Test basic communication
        idn = keithley.query("*IDN?")
        print(f"Connected successfully!")
        print(f"Device ID: {idn.strip()}")
        
        # Reset the device
        keithley.write("*RST")
        keithley.write("*CLS")
        
        # Configure for basic voltage source
        print("\nConfiguring basic voltage source...")
        keithley.write("smu.source.func = smu.FUNC_DC_VOLTAGE")
        keithley.write("smu.source.level = 5.0")
        keithley.write("smu.source.range = 20")
        keithley.write("smu.measure.func = smu.FUNC_DC_CURRENT")
        keithley.write("smu.measure.limit.current = 0.1")  # 100mA limit
        
        # Turn on output
        keithley.write("smu.source.output = smu.ON")
        print("Output enabled - supplying 5V")
        
        # Take a few measurements
        for i in range(5):
            voltage = keithley.query("print(smu.measure.voltage())")
            current = keithley.query("print(smu.measure.current())")
            print(f"Measurement {i+1}: V={float(voltage):.3f}V, I={float(current)*1000:.1f}mA")
            time.sleep(1)
        
        # Turn off output
        keithley.write("smu.source.output = smu.OFF")
        print("\nOutput disabled")
        
        # Close connection
        keithley.close()
        print("Connection closed successfully!")
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        print("\nTroubleshooting:")
        print("1. Check Keithley 2450 is connected via USB")
        print("2. Install Keithley drivers (KI-VISA or NI-VISA)")
        print("3. Update KEITHLEY_ADDRESS in this script")
        print("4. Check Device Manager for correct address")
        return False

if __name__ == "__main__":
    test_keithley_connection()
