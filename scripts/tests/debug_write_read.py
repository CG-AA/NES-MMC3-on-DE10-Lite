#!/usr/bin/env python3
"""
Debug what's actually being read back from SDRAM after writes.
"""

import serial
import time


def mem_write(ser, addr, value):
    """Write and return immediately."""
    cmd = f'mem_write 0x{addr:08x} 0x{value:08x}\r\n'
    ser.write(cmd.encode())


def mem_read_detailed(ser, addr):
    """Read and show full response for debugging."""
    ser.reset_input_buffer()
    ser.write(f'mem_read 0x{addr:08x} 4\r\n'.encode())
    time.sleep(0.1)  # Longer timeout
    resp = ser.read(2048).decode('utf-8', errors='replace')
    return resp


def main():
    ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=2)
    time.sleep(0.1)
    ser.reset_input_buffer()
    ser.write(b'\r\n')
    time.sleep(0.1)
    ser.read(ser.in_waiting)
    
    print("=" * 70)
    print("DEBUG: Write-Read Sequence Analysis")
    print("=" * 70)
    
    base = 0x40000000
    test_values = [0xAAAAAAAA, 0xBBBBBBBB, 0xCCCCCCCC]
    
    print("\n1. SLOW WRITES (10ms between) - Should work:")
    print("-" * 70)
    for i, val in enumerate(test_values):
        addr = base + (i * 4)
        print(f"\nWriting 0x{val:08X} to 0x{addr:08X}")
        mem_write(ser, addr, val)
        time.sleep(0.01)  # 10ms
    
    # Clear buffer before reading
    time.sleep(0.2)
    ser.read(ser.in_waiting)
    
    print("\nReading back...")
    for i, val in enumerate(test_values):
        addr = base + (i * 4)
        resp = mem_read_detailed(ser, addr)
        print(f"\n0x{addr:08X} (expected 0x{val:08X}):")
        print(resp[:200] if len(resp) > 200 else resp)
    
    print("\n" + "=" * 70)
    print("2. FAST WRITES (no delay) - Likely to fail:")
    print("-" * 70)
    
    base2 = 0x40001000
    for i, val in enumerate(test_values):
        addr = base2 + (i * 4)
        print(f"Writing 0x{val:08X} to 0x{addr:08X}")
        mem_write(ser, addr, val)
        # NO DELAY
    
    # Wait for writes to settle
    time.sleep(0.2)
    ser.read(ser.in_waiting)
    
    print("\nReading back...")
    for i, val in enumerate(test_values):
        addr = base2 + (i * 4)
        resp = mem_read_detailed(ser, addr)
        print(f"\n0x{addr:08X} (expected 0x{val:08X}):")
        print(resp[:200] if len(resp) > 200 else resp)
    
    ser.close()


if __name__ == '__main__':
    main()
