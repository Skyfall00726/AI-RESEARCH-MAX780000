#!/usr/bin/env python3
"""
Keithley 2450 Power Measurement System for MAX78000

This script provides power benchmarking for MAX78000 AI inference using the Keithley 2450 SourceMeter.
It automatically processes binary audio files and correlates power measurements with inference results.

Hardware Requirements:
- MAX78000 FeatherBoard
- Keithley 2450 SourceMeter
- Modified USB cable (power path insertion)
- SD card with binary audio test files

Usage:
1. Update the device addresses below
2. Ensure binary files are in /bin/ directory on SD card
3. Run: python keithley_2450_power.py
"""

import serial
from serial import SerialException
from threading import Thread
from threading import Event
from queue import Queue
import ast
import time
import os
import pandas as pd
import re
import datetime
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the device classes
try:
    from smu_devices import Keithley2450SourceMeter, RequestError
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure smu_devices.py is in the same directory")
    sys.exit(1)
from collections import defaultdict, deque
import numpy as np
from typing import NoReturn
from multiprocessing import Process
from multiprocessing import Event as ProcessEvent
from multiprocessing import Queue as ProcessQueue
from dataclasses import dataclass, field


# ===== CONFIGURATION SECTION =====
# Update these addresses for your specific hardware setup

# Keithley 2450 SourceMeter USB address
# Find your device address using NI MAX or Keithley Connection Expert
KEITHLEY_2450_ADDRESS = "USB0::0x05E6::0x2450::04390796::INSTR"

# Serial port for MAX78000 communication
# Check Device Manager (Windows) or /dev/tty* (Linux/Mac)
MAX78000_SERIAL_PORT = "COM10"

# Measurement parameters
SAMPLES_PER_INFERENCE = "10000"  # Number of samples to collect per inference
SAMPLING_RATE = "min"            # "min" for 20μs (50kHz), or specify interval like "50e-6"

# Output directory for results
RESULTS_PATH = "keithley_results"

# ===== END CONFIGURATION =====


# Convert configuration to appropriate types
if SAMPLING_RATE == "min":
    rate_int = float(2e-5)  # 20 microseconds
else:
    rate_int = float(SAMPLING_RATE)
samples_int = int(SAMPLES_PER_INFERENCE)


class PowerCollectionProcess(Process):
    """
    Process for power collection using Keithley 2450
    
    Interfaces with the Keithley 2450 SourceMeter to collect high-resolution
    voltage, current, and power data during MAX78000 inference operations.
    """
    
    def __init__(self, source_meter_name: str, data: defaultdict, data_queue: ProcessQueue, 
                 collection_event: ProcessEvent, ready_event: ProcessEvent, 
                 shutdown_event: ProcessEvent, first_sample: ProcessEvent, buffer_event: ProcessEvent):
        super().__init__()
        self.sm_name = source_meter_name
        self.data_queue = data_queue
        self.collection_event = collection_event
        self.shutdown_event = shutdown_event
        self.ready_event = ready_event
        self.buffer_event = buffer_event
        self.first_sample = first_sample
        self.data = data

    def run(self) -> NoReturn:
        """
        Main process loop for power measurement
        
        Waits for collection events from the main thread and performs
        high-speed power measurements using the Keithley 2450.
        """
        
        # Create Keithley 2450 instance
        source_meter = Keithley2450SourceMeter.get_instance(self.sm_name)

        # Operate entirely within context of the source_meter
        with source_meter as sm:
            
            # Set voltage to 5V and current limit to 100mA
            sm.set_voltage(5.0)
            sm.set_current_limit(100.0)

            # Configure for trace measurements
            sm.configure_trace("defbuffer1", "volt,curr")
            sm.configure_output()

            while not self.shutdown_event.is_set():

                # Wait for measurement trigger
                self.ready_event.wait()
                if self.shutdown_event.is_set():
                    break
            
                self.collection_event.set()
            
                # Clear buffer and prepare for measurement
                sm.clear_trace("defbuffer1")
                sm.start_current()

                self.data = {"Measurements": []}
                trigger_set = False
              
                # Loop to collect power measurements
                while self.collection_event.is_set():
                    if not trigger_set:
                        # Set the trigger for measurements
                        sm.set_trigger(SAMPLING_RATE, SAMPLES_PER_INFERENCE, "defbuffer1")
                        trigger_set = True
                    
                    # Check buffer status
                    buffer_status = sm.get_free_trace("defbuffer1")
                    comma_index = buffer_status.find(",")
                    available = int(buffer_status[:comma_index])

                    # Check if buffer is full (measurement complete)
                    if available <= (100000 - samples_int):
                        # Buffer is full, measurement complete
                        self.buffer_event.set()
                        self.collection_event.clear()

                        if self.shutdown_event.is_set():
                            break
                    
                # Retrieve measurement data
                measurements = sm.retrieve_data("defbuffer1")
                
                # Clear first sample flag
                self.first_sample.clear()

                # Clear buffer for next measurement
                sm.clear_trace("defbuffer1")

                print(f"Collected {len(measurements)} measurement points")
                
                # Prepare data for processing thread
                self.data["Measurements"].append(measurements.flatten().astype(float).tolist())
                
                # Store data in queue
                self.data_queue.put(self.data)


def data_saving(results_path, data: defaultdict, csv_shutdown: Event):
    """
    Thread to save measurement data to CSV files
    
    Processes power measurements and saves them with inference results
    in timestamped CSV files with descriptive filenames.
    """

    while not csv_shutdown.is_set():
        if len(data) != 0:

            # Create directory in "YYYYMMDD" format
            run_date = datetime.datetime.now().strftime("%Y%m%d")
            directory = os.path.join(results_path, run_date)
            os.makedirs(directory, exist_ok=True)
            
            for name, measurements in data.items():
                
                # Create .csv file with descriptive name
                logits = str(name).replace("\r", "").replace("\n", "").replace(" ", "")
                load_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                csv_name = f"{load_time}_{logits}.csv"
                file_path = os.path.join(directory, csv_name)
                
                # Create pandas dataframe
                df = pd.DataFrame()

                # Extract voltage and current from interleaved data
                # Data format: [V1, I1, V2, I2, V3, I3, ...]
                df["Voltage(V)"] = measurements["Measurements"][0][::2]   # Even indices
                df["Current(A)"] = measurements["Measurements"][0][1::2]  # Odd indices
                
                # Calculate power
                voltage_array = np.array(measurements["Measurements"][0][::2])
                current_array = np.array(measurements["Measurements"][0][1::2])
                df["Power(W)"] = voltage_array * current_array
                
                # Save to CSV
                df.to_csv(file_path, index=False)
                print(f"Saved: {csv_name}")
                
            data.clear()


def collect_binaries(ser: serial.Serial):
    """
    Discover binary audio files on MAX78000 SD card
    
    Navigates to /bin/ directory and lists all .bin files
    available for inference testing.
    """

    loop_iteration = 0
    buffer = ""
    while loop_iteration < 3:  
        if ser.in_waiting > 0:
            value = ser.read(ser.in_waiting).decode("ascii")
            buffer += value
            print(value, end='')
        if "$ " in buffer:
            if loop_iteration == 0:
                buffer = ""
                ser.write(("cd bin" + "\r\n").encode(encoding="ascii"))
                loop_iteration += 1
            elif loop_iteration == 1:
                buffer = ""
                ser.write(("ls" + "\r\n").encode(encoding="ascii"))
                loop_iteration += 1
            elif loop_iteration == 2:
                return buffer
    return buffer


if __name__ == "__main__":
    """
    Main Thread for Keithley 2450 Power Benchmarking
    
    Orchestrates the complete power measurement system:
    1. Discovers binary files on MAX78000 SD card
    2. Runs inference on each file via serial commands
    3. Collects synchronized power measurements
    4. Saves results with descriptive filenames
    """

    print("=" * 60)
    print(" MAX78000 Power Benchmarking with Keithley 2450")
    print("=" * 60)
    print(f" SourceMeter: {KEITHLEY_2450_ADDRESS}")
    print(f" Serial Port: {MAX78000_SERIAL_PORT}")
    print(f" Sampling: {samples_int} samples at {rate_int*1e6:.0f} μs intervals")
    print(f" Results: {RESULTS_PATH}/")
    print("=" * 60)

    # Initialize synchronization objects
    shutdown_event = ProcessEvent()
    collection_event = ProcessEvent()
    ready_event = ProcessEvent()
    buffer_event = ProcessEvent()
    first_sample = ProcessEvent()
    data_queue = ProcessQueue()
    csv_shutdown = Event()
    data = defaultdict(list)

    # Create power collection process
    process1 = PowerCollectionProcess(
        source_meter_name=KEITHLEY_2450_ADDRESS,
        data=data,
        data_queue=data_queue,
        collection_event=collection_event,
        ready_event=ready_event,
        shutdown_event=shutdown_event,
        buffer_event=buffer_event,
        first_sample=first_sample
    )
    process1.start()
    time.sleep(7)  # Allow process to initialize

    # Start data saving thread
    data_thread = Thread(target=data_saving, args=(RESULTS_PATH, data, csv_shutdown))
    data_thread.start()

    # Initialize serial communication
    print("Press SW4 Button on MAX78000 to start...")
    ser = serial.Serial(port=MAX78000_SERIAL_PORT, baudrate=115200)
    time.sleep(4)
    
    # Discover binary files on SD card
    print("Discovering binary files on SD card...")
    binaries_string = collect_binaries(ser)
    lines = binaries_string.splitlines()
    command_array = []
    
    for unprocessed_files in lines:
        if unprocessed_files.find(".bin") != -1:
            command_array.append("ri " + unprocessed_files[5:])  
    command_array.append("end")

    print(f"Found {len(command_array)-1} binary files for testing")
    print("Starting power measurements...")

    # Main measurement loop
    command_loop = 0
    buffer = "$ "
    temp_string = ""
    time.sleep(0.06)

    while command_loop < len(command_array):
        try:
            if ser.in_waiting > 0:
                value = ser.read(ser.in_waiting).decode("ascii")
                buffer += value
                temp_string += value
                print(value, end='')
        except SerialException as e:
            print(f"Serial Connection Failed: {e}")
            print("Retrying...")
            ser = serial.Serial(port=MAX78000_SERIAL_PORT, baudrate=115200)
            continue

        # Process command requests
        if "$ " in buffer:
            
            # Extract inference results from previous command
            if command_loop != 0:
                start_marker = "**cah**"
                end_marker = "**hac**"
                if start_marker in temp_string and end_marker in temp_string:
                    key = temp_string[temp_string.find(start_marker) + len(start_marker):temp_string.find(end_marker)]
                    data[key] = data_queue.get()

            # Start power collection for next command
            if command_loop != (len(command_array)-1):
                ready_event.set()
                time.sleep(0.012)  # Allow measurement to start

            # Reset buffers
            buffer = ""
            temp_string = ""
            buffer_event.clear()

            # Send command to MAX78000
            input_command = command_array[command_loop]
            ser.write((input_command + "\r\n").encode(encoding="ascii"))
            
            # Wait for measurement completion
            ready_event.clear()
            if command_loop != (len(command_array)-1):
                buffer_event.wait()  # Wait for buffer to fill
            
            command_loop += 1

    # Cleanup
    print("\nMeasurements complete. Saving final data...")
    time.sleep(0.5)
    csv_shutdown.set()
    shutdown_event.set()
    ready_event.set()

    data_thread.join()
    process1.join()
    
    print("Power benchmarking completed!")
    print(f"Results saved in: {RESULTS_PATH}/")
