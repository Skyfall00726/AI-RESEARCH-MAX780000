# MAX78000 Power Measurement System

## Overview
Complete power measurement system for analyzing MAX78000 AI microcontroller power consumption during keyword spotting inference using Keysight B2901A Precision Source/Measure Unit with 20μs sampling resolution.

## Hardware Requirements
- MAX78000 FeatherBoard
- **Keithley 2450 SourceMeter** (or Keysight B2901A SMU)
- Modified USB cable (power path insertion)
- SD card with binary audio test files

## Key Files
- `keithley_2450_power.py` - **NEW: Keithley 2450 measurement script**
- `smu_sequential_power.py` - Keysight B2901A measurement script
- `smu_devices.py` - SourceMeter interface classes
- `benchmark_*.c` - MAX78000 firmware for power testing
- `pop/` - Complete MAX78000 keyword spotting project

## Quick Start

### For Keithley 2450 (Recommended)
1. Install dependencies: `pip install pandas numpy pyserial pyvisa`
2. Modify USB cable to insert Keithley 2450 in power path
3. Configure device addresses in `keithley_2450_power.py` (lines 25-35)
4. Run: `python keithley_2450_power.py`

### For Keysight B2901A (Original)
1. Install dependencies: `pip install pandas numpy pyserial pyvisa`
2. Modify USB cable to insert B2901A in power path
3. Configure device addresses in `smu_sequential_power.py`
4. Run: `python smu_sequential_power.py`

## Operation
- Automatically processes binary files from SD card `/bin/` folder
- Captures 100,000 samples at 20μs intervals per inference
- Exports voltage, current, and power data to CSV files
- Measures complete inference cycle from file load to CNN completion

## Expected Results
- Idle: 15-25 mA
- Audio processing: 25-40 mA  
- CNN inference: 80-150 mA
- Peak: 200+ mA during memory access

## Configuration

### Keithley 2450 Setup
Update `keithley_2450_power.py`:
```python
KEITHLEY_2450_ADDRESS = "USB0::0x05E6::0x2450::YOUR_SERIAL::INSTR"  # Line 25
MAX78000_SERIAL_PORT = "YOUR_COM_PORT"                              # Line 29
```

### Keysight B2901A Setup  
Update `smu_sequential_power.py`:
```python
source_meter_name="USB0::0x0957::0x8B18::YOUR_SERIAL::INSTR"  # Line 275
ser = serial.Serial(port="YOUR_COM_PORT", baudrate=115200)     # Line 293
```

## Applications
- Inference energy analysis per keyword
- Power consumption comparison across different audio inputs
- Battery life estimation for deployment
- System optimization and power profiling
