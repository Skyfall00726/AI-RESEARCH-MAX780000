"""
Complete Power Measurement System for MAX78000
Combines all necessary components from Christian's architecture into a working system
"""

import serial
from serial import SerialException
import threading
from threading import Thread, Event
from queue import Queue
import time
import os
import pandas as pd
import numpy as np
from datetime import datetime
from collections import defaultdict
from multiprocessing import Process
from multiprocessing import Event as ProcessEvent
from multiprocessing import Queue as ProcessQueue
import pygame
import argparse
import logging
from typing import Optional, Dict, NoReturn
from abc import ABCMeta, abstractmethod

# Core utilities (from Christian's utils.py)
class bidict(dict):
    """A bidirectional dictionary"""
    def __init__(self, *args, **kwargs):
        super(bidict, self).__init__(*args, **kwargs)
        self.inverse = {}
        for key, value in self.items():
            self.inverse.setdefault(value, []).append(key)

    def __setitem__(self, key, value):
        if key in self:
            self.inverse[self[key]].remove(key)
        super(bidict, self).__setitem__(key, value)
        self.inverse.setdefault(value, []).append(key)

class RequestError(Exception):
    pass

# Device classes (from Christian's devices.py)
class AbstractDevice(metaclass=ABCMeta):
    """Abstract Base Class for Devices"""
    _instances: Dict[str, "AbstractDevice"] = dict()

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    @abstractmethod
    def get_device_info(self) -> dict: ...

    @abstractmethod
    def __enter__(self) -> "AbstractDevice": ...

    @abstractmethod
    def __exit__(self, exc_type, exc_value, traceback) -> None: ...

    @classmethod
    def get_instance(cls, name: Optional[str] = None, mock: bool = False, **kwargs):
        if name is not None:
            instance = cls._instances.get(name, None)
        else:
            instance = cls._instances.get("default", None)
        if instance is not None:
            return instance
        instance = cls(name, simulate=mock, **kwargs)
        cls._instances[name or "default"] = instance
        return instance

class AbstractSourceMeter(AbstractDevice):
    """Provides a common interface for Source Meters"""
    
    @abstractmethod
    def measure_current(self) -> np.ndarray: ...

    @abstractmethod
    def measure_voltage(self) -> np.ndarray: ...

    @abstractmethod
    def set_voltage(self, voltage: float) -> None: ...

    @abstractmethod
    def set_current_limit(self, limit: float) -> None: ...

    @abstractmethod
    def configure_output(self) -> None: ...

class TracingSourceMeter(AbstractSourceMeter):
    """Keysight B2901A implementation with trace buffer support"""
    
    def __init__(self, name: Optional[str] = None, simulate: bool = False, **kwargs):
        super().__init__()
        self.name = name or "USB0::0x0957::0x8B18::MY51143212::INSTR"
        self.simulate = simulate
        self.traced = {}
        
        if not simulate:
            try:
                import pyvisa
                self._rm = pyvisa.ResourceManager()
                self._resource = self._rm.open_resource(self.name)
                self._resource.timeout = 30000  # 30 second timeout
                print(f"✅ Connected to SMU: {self.name}")
            except Exception as e:
                print(f"❌ Failed to connect to SMU: {e}")
                print("🔄 Running in simulation mode")
                self.simulate = True
        
        if self.simulate:
            print("⚠️  Running TracingSourceMeter in simulation mode")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if not self.simulate and hasattr(self, '_resource'):
            try:
                self._resource.write(":OUTP OFF")
                self._resource.close()
            except:
                pass

    def get_device_info(self) -> dict:
        if self.simulate:
            return {"name": "SimulatedB2901A", "model": "Simulated", "serial": "SIM123"}
        try:
            idn = self._resource.query("*IDN?")
            return {"name": self.name, "identity": idn.strip()}
        except:
            return {"name": self.name, "identity": "Unknown"}

    def set_voltage(self, voltage: float) -> None:
        if self.simulate:
            print(f"📊 [SIM] Setting voltage: {voltage}V")
            return
        try:
            self._resource.write(f":SOUR:VOLT {voltage}")
        except Exception as e:
            print(f"❌ Error setting voltage: {e}")

    def set_current_limit(self, limit: float) -> None:
        if self.simulate:
            print(f"📊 [SIM] Setting current limit: {limit}A")
            return
        try:
            self._resource.write(f":SOUR:VOLT:ILIM {limit}")
        except Exception as e:
            print(f"❌ Error setting current limit: {e}")

    def configure_trace(self, trace: str, modality: str) -> None:
        """Configure trace buffer for high-speed data collection"""
        if self.simulate:
            print(f"📊 [SIM] Configuring trace: {trace} for {modality}")
            self.traced[trace] = modality
            return
        try:
            self._resource.write(f":{trace}:feed:cont nev")
            self._resource.write(f":{trace}:feed sens")
            self._resource.write(f":form:elem:sense curr,volt")
            self.traced[trace] = modality
        except Exception as e:
            print(f"❌ Error configuring trace: {e}")

    def clear_trace(self, trace: str) -> None:
        """Clear trace buffer"""
        if self.simulate:
            print(f"📊 [SIM] Clearing trace: {trace}")
            return
        try:
            self._resource.write(f":{trace}:clear")
        except Exception as e:
            print(f"❌ Error clearing trace: {e}")

    def get_free_trace(self, trace: str) -> str:
        """Get available trace buffer memory"""
        if self.simulate:
            return "(4800000, 4800000)"  # Simulate full buffer available
        try:
            return self._resource.query(f":{trace}:free?")
        except Exception as e:
            print(f"❌ Error getting trace info: {e}")
            return "(0, 0)"

    def start_current(self) -> None:
        """Start current measurement"""
        if self.simulate:
            print("📊 [SIM] Starting current measurement")
            return
        try:
            self._resource.write(f":trig:acq:del 0")
        except Exception as e:
            print(f"❌ Error starting current measurement: {e}")

    def set_trigger(self, rate: str, samples: str, trace: str = "trac"):
        """Configure trigger for trace buffer"""
        if self.simulate:
            print(f"📊 [SIM] Setting trigger: {rate} rate, {samples} samples")
            return
        try:
            self._resource.write(f":trig:sour tim")
            self._resource.write(f":trig:tim {rate}")
            self._resource.write(f":trig:coun {samples}")
            self._resource.write(f":outp on")
            self._resource.write(f":init:acq")
        except Exception as e:
            print(f"❌ Error setting trigger: {e}")

    def retrieve_data(self, trace: str = "trac") -> np.ndarray:
        """Retrieve data from trace buffer"""
        if self.simulate:
            # Generate simulated power measurement data
            samples = 10000
            time_axis = np.linspace(0, 0.2, samples)  # 200ms measurement
            
            # Simulate realistic power profile: baseline + CNN spike
            baseline_current = 0.015  # 15mA baseline
            cnn_spike_start = 0.05  # CNN starts at 50ms
            cnn_spike_duration = 0.02  # CNN runs for 20ms
            peak_current = 0.120  # 120mA peak during CNN
            
            current = np.full(samples, baseline_current)
            spike_mask = (time_axis >= cnn_spike_start) & (time_axis <= cnn_spike_start + cnn_spike_duration)
            current[spike_mask] = baseline_current + (peak_current - baseline_current) * np.exp(-(time_axis[spike_mask] - cnn_spike_start) * 50)
            
            voltage = np.full(samples, 5.0)  # Stable 5V supply
            
            # Interleave voltage and current (even=voltage, odd=current)
            data = np.zeros(samples * 2)
            data[::2] = voltage
            data[1::2] = current
            
            print(f"📊 [SIM] Retrieved {len(data)} samples from trace")
            return data
        
        try:
            data = self._resource.query_binary_values(f":{trace}:data?", datatype="f", container=np.ndarray, is_big_endian=True)
            return data
        except Exception as e:
            print(f"❌ Error retrieving data: {e}")
            return np.array([])

    def configure_output(self) -> None:
        """Configure output settings"""
        if self.simulate:
            print("📊 [SIM] Configuring output")
            return
        try:
            self._resource.write(":OUTP ON")
        except Exception as e:
            print(f"❌ Error configuring output: {e}")

    def measure_current(self) -> np.ndarray:
        """Single current measurement"""
        if self.simulate:
            return np.array([0.025])  # 25mA
        try:
            result = self._resource.query(":MEAS:CURR?")
            return np.array([float(result)])
        except Exception as e:
            print(f"❌ Error measuring current: {e}")
            return np.array([0.0])

    def measure_voltage(self) -> np.ndarray:
        """Single voltage measurement"""
        if self.simulate:
            return np.array([5.0])  # 5V
        try:
            result = self._resource.query(":MEAS:VOLT?")
            return np.array([float(result)])
        except Exception as e:
            print(f"❌ Error measuring voltage: {e}")
            return np.array([0.0])

# Power collection process (from Christian's architecture)
class PowerCollectionProcess(Process):
    """Dedicated process for power collection"""
    
    def __init__(self, source_meter_name: str, data_queue: ProcessQueue, 
                 collection_event: ProcessEvent, ready_event: ProcessEvent, 
                 shutdown_event: ProcessEvent, buffer_event: ProcessEvent):
        super().__init__()
        self.sm_name = source_meter_name
        self.data_queue = data_queue
        self.collection_event = collection_event
        self.shutdown_event = shutdown_event
        self.ready_event = ready_event
        self.buffer_event = buffer_event

    def run(self) -> NoReturn:
        """Main process loop for power collection"""
        print("🔋 Power collection process started")
        
        # Get SMU instance
        source_meter = TracingSourceMeter.get_instance(self.sm_name)
        
        with source_meter as smu:
            # Configure SMU
            smu.set_voltage(5.0)
            smu.set_current_limit(0.5)  # 500mA limit
            smu.configure_trace("trac", "volt,curr")
            smu.configure_output()
            
            while not self.shutdown_event.is_set():
                # Wait for measurement request
                self.ready_event.wait()
                if self.shutdown_event.is_set():
                    break
                
                print("📊 Starting power measurement...")
                self.collection_event.set()
                
                # Clear trace buffer
                smu.clear_trace("trac")
                smu.start_current()
                
                # Set trigger (20μs intervals, 10000 samples = 200ms window)
                smu.set_trigger("20e-6", "10000", "trac")
                
                # Wait for buffer to fill or collection to stop
                while self.collection_event.is_set():
                    buffer_info = smu.get_free_trace("trac")
                    try:
                        available = int(buffer_info.split(',')[0].strip('('))
                        if available <= 100000:  # Buffer nearly full
                            self.buffer_event.set()
                            self.collection_event.clear()
                            break
                    except:
                        pass
                    
                    if self.shutdown_event.is_set():
                        break
                    
                    time.sleep(0.01)
                
                # Retrieve measurement data
                measurements = smu.retrieve_data("trac")
                
                # Prepare data
                data = {"Measurements": [measurements.flatten().astype(float).tolist()]}
                self.data_queue.put(data)
                
                print(f"✅ Power measurement complete: {len(measurements)} samples")
                self.ready_event.clear()

# Main benchmark class
class CompletePowerBenchmark:
    """Complete power benchmarking system for MAX78000"""
    
    def __init__(self, smu_name, serial_port, audio_dir, results_dir="results"):
        self.smu_name = smu_name
        self.serial_port = serial_port
        self.audio_dir = audio_dir
        self.results_dir = results_dir
        
        # Process synchronization
        self.shutdown_event = ProcessEvent()
        self.collection_event = ProcessEvent()
        self.ready_event = ProcessEvent()
        self.buffer_event = ProcessEvent()
        self.data_queue = ProcessQueue()
        
        # Data storage
        self.power_data = defaultdict(list)
        
        # Serial connection
        self.serial_conn = None
        
        # Initialize pygame for audio playback
        try:
            pygame.mixer.init(frequency=16000, size=-16, channels=1, buffer=512)
            print("🎵 Audio system initialized")
        except Exception as e:
            print(f"⚠️  Audio system initialization failed: {e}")

    def setup_serial(self):
        """Initialize serial connection"""
        try:
            self.serial_conn = serial.Serial(self.serial_port, 115200, timeout=1)
            print(f"✅ Connected to MAX78000 on {self.serial_port}")
            time.sleep(2)
            return True
        except Exception as e:
            print(f"❌ Failed to connect to serial port: {e}")
            return False

    def load_audio_files(self):
        """Load audio files from directory"""
        audio_files = []
        for file in os.listdir(self.audio_dir):
            if file.lower().endswith(('.wav', '.mp3')):
                audio_files.append(os.path.join(self.audio_dir, file))
        print(f"📁 Found {len(audio_files)} audio files")
        return sorted(audio_files)

    def serial_monitor_thread(self):
        """Monitor serial output for keyword detections"""
        buffer = ""
        while not self.shutdown_event.is_set():
            try:
                if self.serial_conn and self.serial_conn.in_waiting > 0:
                    data = self.serial_conn.read(self.serial_conn.in_waiting).decode('utf-8', errors='ignore')
                    buffer += data
                    print(data, end='')
                    
                    # Clear buffer periodically
                    if len(buffer) > 1000:
                        buffer = buffer[-500:]
            except Exception as e:
                print(f"❌ Serial monitor error: {e}")
                break
            time.sleep(0.01)

    def data_saving_thread(self):
        """Save measurement data to CSV files"""
        while not self.shutdown_event.is_set():
            try:
                if not self.data_queue.empty():
                    data = self.data_queue.get(timeout=1)
                    
                    # Process measurement data
                    measurements = data["Measurements"][0]
                    
                    # Split voltage and current (even=voltage, odd=current)
                    voltages = measurements[::2]
                    currents = measurements[1::2]
                    power = np.array(voltages) * np.array(currents)
                    
                    # Create DataFrame
                    df = pd.DataFrame({
                        'Voltage(V)': voltages,
                        'Current(A)': currents,
                        'Power(W)': power
                    })
                    
                    # Save to CSV
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    os.makedirs(self.results_dir, exist_ok=True)
                    csv_path = os.path.join(self.results_dir, f"power_measurement_{timestamp}.csv")
                    df.to_csv(csv_path, index=False)
                    
                    # Print statistics
                    avg_power = np.mean(power) * 1000  # Convert to mW
                    max_power = np.max(power) * 1000
                    print(f"💾 Saved measurement: Avg={avg_power:.1f}mW, Peak={max_power:.1f}mW")
                    
            except Exception as e:
                if not self.shutdown_event.is_set():
                    print(f"❌ Data saving error: {e}")
            time.sleep(0.1)

    def test_audio_file(self, audio_file):
        """Test single audio file with power measurement"""
        filename = os.path.basename(audio_file)
        print(f"\n🎵 Testing: {filename}")
        
        try:
            # Load and play audio
            sound = pygame.mixer.Sound(audio_file)
            duration = sound.get_length()
            
            print(f"⏱️  Audio duration: {duration:.2f}s")
            
            # Start power measurement
            self.ready_event.set()
            time.sleep(0.1)  # Allow measurement to start
            
            # Play audio
            print("🔊 Playing audio...")
            sound.play()
            
            # Wait for audio + detection time
            time.sleep(duration + 2.0)
            
            # Stop measurement
            self.collection_event.clear()
            self.buffer_event.wait(timeout=5)  # Wait for data collection
            
            print(f"✅ Completed: {filename}")
            
        except Exception as e:
            print(f"❌ Error testing {filename}: {e}")

    def run_benchmark(self, test_cycles=1):
        """Run complete benchmark session"""
        print("🚀 Starting Complete Power Benchmark")
        print("=" * 50)
        
        # Setup
        if not self.setup_serial():
            print("⚠️  Continuing without serial connection (simulation mode)")
        
        audio_files = self.load_audio_files()
        if not audio_files:
            print("❌ No audio files found")
            return
        
        # Start power collection process
        power_process = PowerCollectionProcess(
            source_meter_name=self.smu_name,
            data_queue=self.data_queue,
            collection_event=self.collection_event,
            ready_event=self.ready_event,
            shutdown_event=self.shutdown_event,
            buffer_event=self.buffer_event
        )
        power_process.start()
        
        # Start monitoring threads
        serial_thread = Thread(target=self.serial_monitor_thread, daemon=True)
        data_thread = Thread(target=self.data_saving_thread, daemon=True)
        
        serial_thread.start()
        data_thread.start()
        
        print("⏳ Starting benchmark in 3 seconds...")
        time.sleep(3)
        
        try:
            for cycle in range(test_cycles):
                print(f"\n🔄 Test Cycle {cycle + 1}/{test_cycles}")
                
                for audio_file in audio_files:
                    self.test_audio_file(audio_file)
                    time.sleep(3)  # Delay between tests
                    
        except KeyboardInterrupt:
            print("\n⚠️  Benchmark interrupted by user")
        
        finally:
            print("\n🔄 Shutting down...")
            self.shutdown_event.set()
            self.ready_event.set()  # Unblock waiting process
            
            power_process.join(timeout=5)
            if power_process.is_alive():
                power_process.terminate()
            
            if self.serial_conn:
                self.serial_conn.close()
            
            pygame.mixer.quit()
            print("✅ Benchmark complete!")

def main():
    parser = argparse.ArgumentParser(description='Complete Power Benchmark for MAX78000')
    parser.add_argument('--smu', default='USB0::0x0957::0x8B18::MY51143212::INSTR', help='SMU device identifier')
    parser.add_argument('--serial', default='COM3', help='Serial port for MAX78000')
    parser.add_argument('--audio', default='test_audio', help='Directory with test audio files')
    parser.add_argument('--cycles', type=int, default=1, help='Number of test cycles')
    parser.add_argument('--simulate', action='store_true', help='Run in simulation mode')
    
    args = parser.parse_args()
    
    if args.simulate:
        print("🔄 Running in simulation mode")
    
    benchmark = CompletePowerBenchmark(
        smu_name=args.smu,
        serial_port=args.serial,
        audio_dir=args.audio
    )
    
    benchmark.run_benchmark(test_cycles=args.cycles)

if __name__ == "__main__":
    main()
