#!/usr/bin/env python3
"""
Rapid Write Test - Find minimum reliable delay

Goal: Binary search to find the minimum delay needed between writes.
Since individual writes work, this tests only the timing threshold.
"""

import serial
import time
import random


def mem_write_block(ser, base_addr, count, delay_ms):
    """Write a block of random data with specified delay."""
    test_data = [random.randint(0, 0xFFFFFFFF) for _ in range(count)]
    
    # Write
    ser.reset_input_buffer()
    for i, value in enumerate(test_data):
        addr = base_addr + (i * 4)
        cmd = f'mem_write 0x{addr:08x} 0x{value:08x}\r\n'
        ser.write(cmd.encode())
        
        if delay_ms > 0:
            time.sleep(delay_ms / 1000.0)
        
        # Prevent buffer overflow
        if ser.in_waiting > 200:
            ser.read(ser.in_waiting)
    
    # Flush
    time.sleep(0.1)
    ser.read(ser.in_waiting)
    
    return test_data


def verify_block(ser, base_addr, test_data):
    """Verify written data - sample 16 random locations."""
    errors = 0
    sample_indices = random.sample(range(len(test_data)), min(16, len(test_data)))
    
    for i in sample_indices:
        addr = base_addr + (i * 4)
        expected = test_data[i]
        
        ser.reset_input_buffer()
        ser.write(f'mem_read 0x{addr:08x} 4\r\n'.encode())
        time.sleep(0.05)
        resp = ser.read(1024).decode('utf-8', errors='replace')
        
        # Parse
        actual = None
        for line in resp.split('\n'):
            if f'0x{addr:08x}' in line.lower():
                parts = line.split()
                if len(parts) >= 5:
                    try:
                        b = [int(parts[j], 16) for j in range(1, 5)]
                        actual = b[0] | (b[1] << 8) | (b[2] << 16) | (b[3] << 24)
                    except:
                        pass
        
        if actual != expected:
            errors += 1
    
    return errors == 0


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', default='/dev/ttyUSB0')
    args = parser.parse_args()
    
    ser = serial.Serial(args.port, 115200, timeout=2)
    time.sleep(0.1)
    ser.reset_input_buffer()
    ser.write(b'\r\n')
    time.sleep(0.1)
    ser.read(ser.in_waiting)
    
    print("=" * 70)
    print("RAPID WRITE TEST - Finding Minimum Reliable Delay")
    print("=" * 70)
    
    base = 0x40000000
    block_size = 256  # 1KB block for quick testing
    
    # Test different delays
    delays = [0, 0.5, 1, 2, 5, 10]
    
    results = {}
    
    for delay in delays:
        print(f"\nTesting {delay}ms delay ({block_size} words = {block_size*4} bytes)...")
        
        data = mem_write_block(ser, base, block_size, delay)
        success = verify_block(ser, base, data)
        results[delay] = success
        
        status = "✓ PASS" if success else "✗ FAIL"
        rate = (block_size * 4) / ((delay * block_size / 1000.0) + 0.1) if delay > 0 else 999999
        print(f"  {status} - Effective rate: {rate:.0f} B/s")
    
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    for delay, success in results.items():
        status = "✓" if success else "✗"
        print(f"{status} {delay:4.1f}ms delay")
    
    # Find threshold
    working = [d for d, s in results.items() if s]
    failing = [d for d, s in results.items() if not s]
    
    if working:
        print(f"\nMinimum working delay: {min(working)}ms")
    if failing:
        print(f"Maximum failing delay: {max(failing)}ms")
    
    ser.close()


if __name__ == '__main__':
    main()
