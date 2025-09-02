#!/usr/bin/env python3
"""
Test script for the complete power measurement system
Verifies all components work correctly before running actual benchmarks
"""

from complete_power_system import TracingSourceMeter, CompletePowerBenchmark
import os
import tempfile

def test_smu_connection():
    """Test SMU connection and basic functionality"""
    print("🔧 Testing SMU Connection...")
    
    try:
        # Test with simulation mode first
        smu = TracingSourceMeter.get_instance("test_smu", simulate=True)
        
        with smu as device:
            # Test basic operations
            device.set_voltage(5.0)
            device.set_current_limit(0.5)
            device.configure_trace("trac", "volt,curr")
            device.configure_output()
            
            # Test measurement
            voltage = device.measure_voltage()
            current = device.measure_current()
            
            print(f"✅ Simulation test passed: V={voltage[0]:.2f}V, I={current[0]*1000:.1f}mA")
            
            # Test trace buffer
            device.clear_trace("trac")
            device.start_current()
            device.set_trigger("20e-6", "1000", "trac")
            
            data = device.retrieve_data("trac")
            print(f"✅ Trace buffer test passed: {len(data)} samples retrieved")
            
        return True
        
    except Exception as e:
        print(f"❌ SMU test failed: {e}")
        return False

def test_audio_system():
    """Test audio playback system"""
    print("🎵 Testing Audio System...")
    
    try:
        import pygame
        pygame.mixer.init(frequency=16000, size=-16, channels=1, buffer=512)
        
        # Create a simple test tone
        import numpy as np
        duration = 0.5  # 500ms
        sample_rate = 16000
        frequency = 1000  # 1kHz tone
        
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        wave = np.sin(2 * np.pi * frequency * t)
        
        # Convert to pygame sound format
        wave = (wave * 32767).astype(np.int16)
        sound = pygame.sndarray.make_sound(wave.reshape(-1, 1))
        
        print("🔊 Playing test tone...")
        sound.play()
        
        import time
        time.sleep(duration + 0.1)
        
        pygame.mixer.quit()
        print("✅ Audio system test passed")
        return True
        
    except Exception as e:
        print(f"❌ Audio test failed: {e}")
        return False

def test_file_operations():
    """Test file I/O operations"""
    print("📁 Testing File Operations...")
    
    try:
        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test CSV writing
            import pandas as pd
            import numpy as np
            
            test_data = pd.DataFrame({
                'Voltage(V)': np.full(100, 5.0),
                'Current(A)': np.random.uniform(0.01, 0.1, 100),
                'Power(W)': np.random.uniform(0.05, 0.5, 100)
            })
            
            csv_path = os.path.join(temp_dir, "test_measurement.csv")
            test_data.to_csv(csv_path, index=False)
            
            # Verify file was created and is readable
            loaded_data = pd.read_csv(csv_path)
            assert len(loaded_data) == 100
            assert 'Power(W)' in loaded_data.columns
            
            print("✅ File operations test passed")
            return True
            
    except Exception as e:
        print(f"❌ File operations test failed: {e}")
        return False

def test_benchmark_initialization():
    """Test benchmark class initialization"""
    print("🚀 Testing Benchmark Initialization...")
    
    try:
        # Create temporary audio directory
        with tempfile.TemporaryDirectory() as temp_dir:
            benchmark = CompletePowerBenchmark(
                smu_name="test_smu",
                serial_port="COM999",  # Non-existent port for testing
                audio_dir=temp_dir
            )
            
            # Test audio file loading (empty directory)
            audio_files = benchmark.load_audio_files()
            assert audio_files == []
            
            # Create dummy audio file
            dummy_audio = os.path.join(temp_dir, "test.wav")
            with open(dummy_audio, 'wb') as f:
                f.write(b"RIFF" + b"\x00" * 40)  # Minimal WAV header
            
            audio_files = benchmark.load_audio_files()
            assert len(audio_files) == 1
            
            print("✅ Benchmark initialization test passed")
            return True
            
    except Exception as e:
        print(f"❌ Benchmark initialization test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing Complete Power Measurement System")
    print("=" * 50)
    
    tests = [
        ("SMU Connection", test_smu_connection),
        ("Audio System", test_audio_system),
        ("File Operations", test_file_operations),
        ("Benchmark Init", test_benchmark_initialization)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}:")
        if test_func():
            passed += 1
        else:
            print(f"⚠️  {test_name} test failed")
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! System is ready for benchmarking.")
        print("\n🚀 To run actual benchmark:")
        print("   python complete_power_system.py --audio your_audio_dir --simulate")
        print("   (Use --simulate flag first to test without hardware)")
    else:
        print("❌ Some tests failed. Please check the error messages above.")
    
    return passed == total

if __name__ == "__main__":
    main()
