#!/usr/bin/env python3
"""
Quick test of SDRAM fixes - verify synchronous flow control works.
Tests just a few writes to confirm the improvements.
"""

import serial
import time
import random


def send_command_sync(ser, cmd: str, timeout: float = 2.0) -> str:
    """Send command and wait for prompt - handles ANSI codes."""
    ser.write(cmd.encode() + b'\r\n')
    
    response = b''
    start = time.time()
    while True:
        if ser.in_waiting > 0:
            chunk = ser.read(ser.in_waiting)
            response += chunk
            # Check for prompt in raw bytes (handles ANSI codes)
            if b'litex>' in response or b'LITEX>' in response:
                return response.decode('utf-8', errors='replace')
        
        if time.time() - start > timeout:
            print(f"TIMEOUT waiting for prompt after: {cmd[:50]}")
            return response.decode('utf-8', errors='replace')
        
        time.sleep(0.01)


def quick_test(ser):
    """Quick test: write a few values, read them back."""
    print("\n" + "="*70)
    print("QUICK SDRAM TEST")
    print("="*70)
    
    base = 0x40000000
    test_data = [
        (0x00, 0xDEADBEEF),
        (0x04, 0xCAFEBABE),
        (0x08, 0x12345678),
        (0x0C, 0xABCDEF00),
        (0x1000, 0x11111111),  # Different page
        (0x2000, 0x22222222),  # Another page
    ]
    
    print("\n1. Writing test values with synchronous flow control...")
    start = time.time()
    
    for offset, value in test_data:
        addr = base + offset
        cmd = f'mem_write 0x{addr:08x} 0x{value:08x}'
        response = send_command_sync(ser, cmd)
        print(f"  0x{addr:08X} ← 0x{value:08X} ... ", end='')
        if 'litex>' in response.lower():
            print("✓")
        else:
            print(f"⚠ (no prompt seen)")
    
    elapsed = time.time() - start
    print(f"\nWrites completed in {elapsed:.1f}s")
    
    print("\n2. Reading back and verifying...")
    errors = 0
    
    for offset, expected in test_data:
        addr = base + offset
        response = send_command_sync(ser, f'mem_read 0x{addr:08x} 4')
        
        # Parse response
        actual = None
        for line in response.split('\n'):
            if '0x40' in line and ':' in line:
                parts = line.split()
                if len(parts) >= 5:
                    try:
                        b = [int(parts[j], 16) for j in range(1, 5)]
                        actual = b[0] | (b[1] << 8) | (b[2] << 16) | (b[3] << 24)
                    except:
                        pass
        
        status = "✓" if actual == expected else f"✗ (got 0x{actual:08X if actual else 0:08X})"
        print(f"  0x{addr:08X}: {status}")
        
        if actual != expected:
            errors += 1
    
    print("\n" + "="*70)
    if errors == 0:
        print("✓ TEST PASSED - All values verified correctly!")
        print("Synchronous flow control is working.")
        return True
    else:
        print(f"✗ TEST FAILED - {errors}/{len(test_data)} errors")
        return False


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', default='/dev/ttyUSB0')
    args = parser.parse_args()
    
    print(f"Connecting to {args.port}...")
    ser = serial.Serial(args.port, 115200, timeout=2)
    time.sleep(0.2)
    
    # Clear and get to prompt
    ser.reset_input_buffer()
    ser.write(b'\r\n\r\n')
    time.sleep(0.2)
    initial_bytes = ser.read(ser.in_waiting)
    initial = initial_bytes.decode('utf-8', errors='replace')
    print(f"Connection established")
    
    # Check for prompt (handles ANSI codes in bytes)
    if b'litex' not in initial_bytes and b'LITEX' not in initial_bytes:
        print("\n⚠ WARNING: BIOS prompt not detected")
        print(f"Got: {initial[:100]}")
        print("FPGA may need reprogramming:")
        print("  python3 terasic_de10lite_custom.py --build")
        print("  python3 terasic_de10lite_custom.py --load")
        ser.close()
        return
    
    try:
        success = quick_test(ser)
        
        if success:
            print("\n✓ Fixes appear to be working!")
            print("  - Synchronous flow control: OK")
            print("  - Data persistence: OK")
            print("\nReady to test full ROM upload with:")
            print("  python3 upload_rom.py donkey_kong.nes")
        else:
            print("\n✗ Issues remain - check SDRAM timings and rebuild")
    
    finally:
        ser.close()


if __name__ == '__main__':
    main()
