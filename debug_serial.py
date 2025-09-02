#!/usr/bin/env python3
"""
Debug serial connection to MAX78000
"""
import serial
import time
import sys

def debug_serial(port='COM4', baudrate=115200):
    print(f"🔍 Debugging MAX78000 on {port}")
    print("=" * 50)
    
    try:
        # Try to connect
        print(f"1️⃣ Attempting to connect to {port}...")
        ser = serial.Serial(port, baudrate, timeout=1)
        print(f"✅ Connected successfully!")
        print(f"   Port: {ser.port}")
        print(f"   Baud: {ser.baudrate}")
        print(f"   Is Open: {ser.is_open}")
        print()
        
        # Check initial state
        print("2️⃣ Checking initial buffer...")
        if ser.in_waiting > 0:
            initial_data = ser.read_all().decode('utf-8', errors='ignore')
            print(f"✅ Found {len(initial_data)} bytes of data!")
            print(f"Data: {repr(initial_data)}")
        else:
            print("⚠️ No initial data in buffer")
        print()
        
        # Send some test data to see if board responds
        print("3️⃣ Testing board responsiveness...")
        test_chars = ['\r', '\n', ' ', 'h', 'i', '\r\n']
        for char in test_chars:
            print(f"   Sending: {repr(char)}")
            ser.write(char.encode())
            time.sleep(0.5)
            if ser.in_waiting > 0:
                response = ser.read_all().decode('utf-8', errors='ignore')
                print(f"   📨 Response: {repr(response)}")
            else:
                print("   📭 No response")
        print()
        
        # Long listen test
        print("4️⃣ Listening for 10 seconds...")
        print("   💡 Try pressing RESET (SW4) on your MAX78000 now!")
        print("   💡 Or try saying 'hello' or 'yes' near the microphone")
        
        start_time = time.time()
        total_data = ""
        
        while time.time() - start_time < 10:
            if ser.in_waiting > 0:
                data = ser.read_all().decode('utf-8', errors='ignore')
                total_data += data
                print(f"   📨 Received: {repr(data)}")
            time.sleep(0.1)
        
        if total_data:
            print(f"\n🎉 SUCCESS! Total data received: {len(total_data)} bytes")
            print(f"Full data: {repr(total_data)}")
        else:
            print(f"\n❌ No data received in 10 seconds")
            print("Possible issues:")
            print("   • Board not powered or not running firmware")
            print("   • Wrong COM port (try unplugging/replugging USB)")
            print("   • Firmware might be waiting for button press")
            print("   • Board might be in sleep mode")
        
        ser.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    debug_serial()
