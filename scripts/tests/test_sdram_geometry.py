#!/usr/bin/env python3
"""
SDRAM Geometry Probe Test

Goal: Determine if the Address/Bank mapping is misaligned.

The IS42S16320 has:
- 10 Column bits
- 13 Row bits  
- 4 Banks (2 bits)
- 16-bit bus (2 bytes per word)

Page Size = 2^10 words × 2 bytes = 2048 bytes (0x800)

This test writes to specific address boundaries to detect:
1. Row/column bit misalignment
2. Bank initialization issues
3. Address aliasing problems
"""

import serial
import time
import argparse


def mem_write(ser, addr, value):
    """Write a 32-bit value to SDRAM."""
    ser.reset_input_buffer()
    cmd = f'mem_write 0x{addr:08x} 0x{value:08x}\r\n'
    ser.write(cmd.encode())
    time.sleep(0.01)  # Ensure write completes
    # Discard response
    ser.read(ser.in_waiting)


def mem_read(ser, addr):
    """Read a 32-bit value from SDRAM."""
    ser.reset_input_buffer()
    ser.write(f'mem_read 0x{addr:08x} 4\r\n'.encode())
    time.sleep(0.05)
    resp = ser.read(1024).decode('utf-8', errors='replace')
    
    # Parse response - look for hex bytes
    for line in resp.split('\n'):
        if f'0x{addr:08x}' in line.lower():
            parts = line.split()
            if len(parts) >= 5:
                try:
                    # Response format: "0x40000000: AA BB CC DD"
                    b = [int(parts[j], 16) for j in range(1, 5)]
                    # Little endian: DD CC BB AA
                    value = b[0] | (b[1] << 8) | (b[2] << 16) | (b[3] << 24)
                    return value
                except:
                    pass
    return None


def test_geometry(ser):
    """Test SDRAM geometry at specific boundaries."""
    
    # Page Size = 0x800 (2048 bytes)
    # Testing addresses at different row/bank boundaries
    targets = {
        0x40000000: "Row 0, Bank 0, Start (Base)",
        0x400007FC: "Row 0, Bank 0, End (last word before boundary)",
        0x40000800: "Row 1, Bank 0, Start (Page boundary 1)",
        0x40001000: "Row 2, Bank 0, Start (Page boundary 2)",
        0x40001800: "Row 3, Bank 0, Start (Page boundary 3)",
        0x40002000: "Row 4, Bank 0, Start (Page boundary 4)",
        0x40004000: "Row 8, Bank 0, Start",
        0x40008000: "Row 16, Bank 0, Start",
    }
    
    print("=" * 70)
    print("SDRAM GEOMETRY PROBE TEST")
    print("=" * 70)
    print(f"IS42S16320 Expected Configuration:")
    print(f"  - 10 Column bits → Page size = 2^10 words × 2 bytes = 2048 bytes (0x800)")
    print(f"  - 13 Row bits")
    print(f"  - 4 Banks (2 bits)")
    print(f"  - 16-bit data bus")
    print()
    print("Testing address boundaries to detect mapping issues...")
    print("=" * 70)
    print()
    
    test_value = 0xDEADBEEF
    results = {}
    
    for addr in sorted(targets.keys()):
        desc = targets[addr]
        
        # Write test value
        mem_write(ser, addr, test_value)
        
        # Small delay to ensure write completes
        time.sleep(0.01)
        
        # Read back
        actual = mem_read(ser, addr)
        
        # Determine status
        if actual == test_value:
            status = "✓ OK"
            results[addr] = True
        elif actual is None:
            status = "✗ FAIL (No response)"
            results[addr] = False
        else:
            status = f"✗ FAIL (Got 0x{actual:08X})"
            results[addr] = False
        
        print(f"0x{addr:08X} [{desc}]")
        print(f"  Expected: 0x{test_value:08X}")
        print(f"  Result:   {status}")
        print()
    
    # Analysis
    print("=" * 70)
    print("ANALYSIS")
    print("=" * 70)
    
    working = [addr for addr, ok in results.items() if ok]
    failing = [addr for addr, ok in results.items() if not ok]
    
    print(f"Working addresses: {len(working)}/{len(results)}")
    for addr in working:
        print(f"  ✓ 0x{addr:08X}")
    print()
    
    print(f"Failing addresses: {len(failing)}/{len(results)}")
    for addr in failing:
        print(f"  ✗ 0x{addr:08X}")
    print()
    
    # Specific patterns to look for
    if not results.get(0x40000000) and not results.get(0x40000800):
        if results.get(0x40001000):
            print("⚠ DIAGNOSIS: Base and first page boundary fail, but 0x1000 works")
            print("   → Likely address bit shift or Bank 0/Row 0-1 initialization issue")
            print("   → Controller may be driving Addr[0] to wrong pin")
            print()
    
    if not results.get(0x40000000) and results.get(0x40000800):
        print("⚠ DIAGNOSIS: Base address fails but page boundary works")
        print("   → Row 0 may be locked by refresh or initialization issue")
        print("   → Bank 0 column 0 may have mapping problem")
        print()
    
    if all(results.get(addr) for addr in [0x40001000, 0x40002000]) and not results.get(0x40000000):
        print("⚠ DIAGNOSIS: Higher addresses work, base address fails")
        print("   → SDRAM controller may have wrong base address offset")
        print("   → First row/bank not properly activated")
        print()
    
    # Test for aliasing
    if len(working) > 1:
        print("Testing for address aliasing...")
        base = working[0]
        test_val_1 = 0x11111111
        test_val_2 = 0x22222222
        
        # Write different values to two working addresses
        if len(working) >= 2:
            addr1 = working[0]
            addr2 = working[1]
            
            mem_write(ser, addr1, test_val_1)
            time.sleep(0.01)
            mem_write(ser, addr2, test_val_2)
            time.sleep(0.01)
            
            # Read back both
            val1 = mem_read(ser, addr1)
            val2 = mem_read(ser, addr2)
            
            print(f"  Write 0x{test_val_1:08X} to 0x{addr1:08X}")
            print(f"  Write 0x{test_val_2:08X} to 0x{addr2:08X}")
            val1_str = f"0x{val1:08X}" if val1 is not None else "None"
            val2_str = f"0x{val2:08X}" if val2 is not None else "None"
            print(f"  Read back 0x{addr1:08X}: {val1_str}")
            print(f"  Read back 0x{addr2:08X}: {val2_str}")
            
            if val1 == test_val_2 or val2 == test_val_1:
                print("  ✗ ALIASING DETECTED! Addresses map to same physical location")
            else:
                print("  ✓ No aliasing - addresses are independent")
        print()
    
    return results


def main():
    parser = argparse.ArgumentParser(description='Test SDRAM address geometry')
    parser.add_argument('--port', default='/dev/ttyUSB0', help='Serial port')
    parser.add_argument('--baud', type=int, default=115200, help='Baud rate')
    args = parser.parse_args()
    
    print(f"Connecting to {args.port} at {args.baud} baud...")
    ser = serial.Serial(args.port, args.baud, timeout=2)
    time.sleep(0.1)
    
    # Clear any pending data
    ser.reset_input_buffer()
    
    # Send a newline to ensure we're at a prompt
    ser.write(b'\r\n')
    time.sleep(0.1)
    ser.read(ser.in_waiting)
    
    try:
        test_geometry(ser)
    finally:
        ser.close()
    
    print("Test complete!")


if __name__ == '__main__':
    main()
