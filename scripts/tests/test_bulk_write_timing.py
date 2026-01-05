#!/usr/bin/env python3
"""
SDRAM Bulk Write Timing Test

Goal: Determine why individual writes work but bulk uploads fail.

This test writes blocks of data at different speeds to find the timing threshold
where the SDRAM controller starts dropping writes.
"""

import serial
import time
import struct
import random


def mem_write(ser, addr, value):
    """Write a 32-bit value to SDRAM."""
    cmd = f'mem_write 0x{addr:08x} 0x{value:08x}\r\n'
    ser.write(cmd.encode())


def mem_read(ser, addr):
    """Read a 32-bit value from SDRAM."""
    ser.reset_input_buffer()
    ser.write(f'mem_read 0x{addr:08x} 4\r\n'.encode())
    time.sleep(0.05)
    resp = ser.read(1024).decode('utf-8', errors='replace')
    
    # Parse response
    for line in resp.split('\n'):
        if f'0x{addr:08x}' in line.lower():
            parts = line.split()
            if len(parts) >= 5:
                try:
                    b = [int(parts[j], 16) for j in range(1, 5)]
                    value = b[0] | (b[1] << 8) | (b[2] << 16) | (b[3] << 24)
                    return value
                except:
                    pass
    return None


def test_bulk_write(ser, base_addr, size_bytes, delay_ms, description):
    """Write a block of data with specified delay between writes."""
    
    print(f"\n{'='*70}")
    print(f"TEST: {description}")
    print(f"{'='*70}")
    print(f"Base address: 0x{base_addr:08X}")
    print(f"Size: {size_bytes} bytes ({size_bytes//1024}KB)")
    print(f"Delay: {delay_ms}ms between writes")
    
    # Generate test data
    num_words = size_bytes // 4
    test_data = [random.randint(0, 0xFFFFFFFF) for _ in range(num_words)]
    
    # Write phase
    print("\nWriting...")
    ser.reset_input_buffer()
    start = time.time()
    
    for i, value in enumerate(test_data):
        addr = base_addr + (i * 4)
        mem_write(ser, addr, value)
        
        if delay_ms > 0:
            time.sleep(delay_ms / 1000.0)
        
        # Occasionally clear the input buffer to prevent overflow
        if i % 32 == 0 and ser.in_waiting > 100:
            ser.read(ser.in_waiting)
        
        # Progress
        if i % 256 == 0:
            print(f"  {i}/{num_words} words written ({i*100//num_words}%)")
    
    # Final buffer clear
    time.sleep(0.1)
    ser.read(ser.in_waiting)
    
    elapsed = time.time() - start
    rate = size_bytes / elapsed
    print(f"Write complete: {elapsed:.1f}s ({rate:.0f} B/s)")
    
    # Verification phase - sample random addresses
    print("\nVerifying...")
    sample_size = min(64, num_words)
    sample_indices = random.sample(range(num_words), sample_size)
    
    errors = 0
    for i in sample_indices:
        addr = base_addr + (i * 4)
        expected = test_data[i]
        actual = mem_read(ser, addr)
        
        if actual != expected:
            errors += 1
            if errors <= 5:  # Only print first 5 errors
                print(f"  ✗ ERROR at 0x{addr:08X}: expected 0x{expected:08X}, got {actual}")
    
    if errors == 0:
        print(f"  ✓ ALL {sample_size} samples verified OK")
        return True
    else:
        print(f"  ✗ {errors}/{sample_size} errors ({errors*100//sample_size}% failure rate)")
        return False


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Test SDRAM bulk write timing')
    parser.add_argument('--port', default='/dev/ttyUSB0', help='Serial port')
    parser.add_argument('--baud', type=int, default=115200, help='Baud rate')
    args = parser.parse_args()
    
    print(f"Connecting to {args.port} at {args.baud} baud...")
    ser = serial.Serial(args.port, args.baud, timeout=2)
    time.sleep(0.1)
    
    # Clear any pending data
    ser.reset_input_buffer()
    ser.write(b'\r\n')
    time.sleep(0.1)
    ser.read(ser.in_waiting)
    
    print("\n" + "="*70)
    print("SDRAM BULK WRITE TIMING TEST")
    print("="*70)
    print("This test will write blocks of data at different speeds to find")
    print("the timing threshold where writes start to fail.")
    
    tests = [
        # (base_addr, size, delay_ms, description)
        (0x40000000, 1024, 10, "1KB block, 10ms delay (known working)"),
        (0x40000000, 4096, 10, "4KB block, 10ms delay"),
        (0x40000000, 8192, 10, "8KB block, 10ms delay"),
        (0x40000000, 4096, 5, "4KB block, 5ms delay"),
        (0x40000000, 4096, 2, "4KB block, 2ms delay"),
        (0x40000000, 4096, 1, "4KB block, 1ms delay"),
        (0x40000000, 4096, 0, "4KB block, NO delay (back-to-back)"),
        (0x40000000, 32768, 10, "32KB block, 10ms delay (full PRG ROM size)"),
    ]
    
    results = []
    
    try:
        for test_params in tests:
            success = test_bulk_write(ser, *test_params)
            results.append((test_params[3], success))
            
            # Wait between tests
            time.sleep(0.5)
    
    finally:
        ser.close()
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    for desc, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {desc}")
    
    print("\nTest complete!")


if __name__ == '__main__':
    main()
