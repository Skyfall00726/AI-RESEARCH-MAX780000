#!/usr/bin/env python3
import serial
import time

def reset_test():
    ports = ['COM3', 'COM4', 'COM5']
    
    for port in ports:
        print(f"\n🔍 Testing {port}...")
        try:
            ser = serial.Serial(port, 115200, timeout=0.5)
            print(f"✅ Connected to {port}")
            print("🔴 PRESS AND RELEASE RESET (SW4) ON YOUR BOARD NOW!")
            print("Listening for 15 seconds...")
            
            start_time = time.time()
            received_any_data = False
            
            while time.time() - start_time < 15:
                if ser.in_waiting > 0:
                    data = ser.read_all().decode('utf-8', errors='ignore')
                    if data:
                        received_any_data = True
                        print(f"📨 RECEIVED: {repr(data)}")
                        print(f"📨 TEXT: {data}")
                time.sleep(0.1)
            
            if received_any_data:
                print(f"🎉 SUCCESS! {port} is the correct port!")
                ser.close()
                return port
            else:
                print(f"❌ No data from {port}")
            
            ser.close()
            
        except Exception as e:
            print(f"❌ Cannot connect to {port}: {e}")
    
    print("\n❌ No working serial port found")
    return None

if __name__ == "__main__":
    print("🔍 MAX78000 Reset Test")
    print("=" * 50)
    working_port = reset_test()
    
    if working_port:
        print(f"\n✅ Your MAX78000 serial port is: {working_port}")
        print("✅ Serial communication is working!")
    else:
        print("\n❌ Serial communication issue detected")
        print("Possible solutions:")
        print("• Check USB cable connection")
        print("• Try a different USB port")
        print("• Check if board is powered (LED should be on)")
        print("• Try unplugging and reconnecting USB cable")
