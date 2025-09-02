#!/usr/bin/env python3
"""
Real-time serial monitor for MAX78000 FeatherBoard
Press Ctrl+C to exit
"""
import serial
import time
import sys
from datetime import datetime

def serial_monitor(port='COM10', baudrate=115200):
    try:
        print(f"🔗 Connecting to {port} at {baudrate} baud...")
        ser = serial.Serial(port, baudrate, timeout=0.1)
        print(f"✅ Connected to {port}")
        print("=" * 60)
        print("📺 MAX78000 Serial Monitor - Press Ctrl+C to exit")
        print("💡 Try pressing RESET (SW4) on your MAX78000 board")
        print("🎤 Try saying keywords: 'up', 'down', 'yes', 'no', etc.")
        print("=" * 60)
        
        buffer = ""
        last_activity = time.time()
        
        while True:
            if ser.in_waiting > 0:
                data = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                buffer += data
                last_activity = time.time()
                
                # Process complete lines
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    print(f"[{timestamp}] {line}")
                
                # Print partial data if it ends with \r or other terminators
                if buffer and (buffer.endswith('\r') or len(buffer) > 100):
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    print(f"[{timestamp}] {buffer}", end='')
                    buffer = ""
            
            # Show activity indicator
            if time.time() - last_activity > 5:
                print("💤 No activity - try pressing RESET on your board...")
                last_activity = time.time() + 10  # Don't spam this message
            
            time.sleep(0.01)  # Small delay to prevent high CPU usage
            
    except serial.SerialException as e:
        print(f"❌ Serial connection error: {e}")
        print("💡 Make sure your MAX78000 is connected and no other program is using the port")
    except KeyboardInterrupt:
        print("\n\n👋 Serial monitor stopped by user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print(f"🔌 Disconnected from {port}")

if __name__ == "__main__":
    print("🚀 MAX78000 Real-time Serial Monitor")
    print("=" * 50)
    
    # Check if user wants to specify a different port
    if len(sys.argv) > 1:
        port = sys.argv[1]
    else:
        port = 'COM10'  # Default based on our detection
    
    serial_monitor(port)
