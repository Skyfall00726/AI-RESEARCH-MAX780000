#!/usr/bin/env python3
"""
Simple serial monitor for MAX78000 FeatherBoard
"""
import serial
import time
import sys

def test_serial_connection():
    ports_to_try = ['COM3', 'COM4', 'COM5', 'COM6']  # Try multiple ports
    
    for port in ports_to_try:
        try:
            print(f"Trying {port}...")
            ser = serial.Serial(port, 115200, timeout=2)
            print(f"✅ Connected to {port}")
            
            print("Waiting for data (5 seconds)...")
            start_time = time.time()
            received_data = ""
            
            while time.time() - start_time < 5:
                if ser.in_waiting > 0:
                    data = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                    received_data += data
                    print(data, end='', flush=True)
                time.sleep(0.1)
            
            if received_data:
                print(f"\n\n🎉 SUCCESS! Received data from {port}")
                print(f"Data: {repr(received_data)}")
            else:
                print(f"\n⚠️ No data received from {port}")
                print("Try pressing the RESET button on your MAX78000 board")
            
            ser.close()
            return port, received_data
            
        except serial.SerialException as e:
            print(f"❌ Could not connect to {port}: {e}")
        except Exception as e:
            print(f"❌ Error with {port}: {e}")
    
    print("❌ Could not connect to any COM port")
    return None, None

if __name__ == "__main__":
    print("🔍 MAX78000 Serial Port Scanner")
    print("=" * 40)
    port, data = test_serial_connection()
    
    if port:
        print(f"\n✅ Your MAX78000 is on {port}")
        print("💡 Use these settings in your terminal program:")
        print(f"   Port: {port}")
        print("   Baud Rate: 115200")
        print("   Data Bits: 8")
        print("   Stop Bits: 1")
        print("   Parity: None")
        print("   Flow Control: None")
    else:
        print("\n❌ No MAX78000 found. Check connections and try again.")
