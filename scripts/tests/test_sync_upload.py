#!/usr/bin/env python3
"""
Test synchronous upload with flow control.

This test uses the new send_command_sync function that waits for
the BIOS prompt after each command, ensuring proper flow control.
"""

import serial
import time
import random
import struct


def send_command_sync(ser, cmd: str, timeout: float = 1.0) -> str:
    """Send command and wait for BIOS prompt."""
    ser.write(cmd.encode() + b'\r\n')
    
    response = b''
    start = time.time()
    while True:
        if ser.in_waiting > 0:
            chunk = ser.read(ser.in_waiting)
            response += chunk
            # Check for prompt (with or without ANSI codes)
            if b'litex' in response and b'>' in response:
                return response.decode('utf-8', errors='replace')
        
        if time.time() - start > timeout:
            return response.decode('utf-8', errors='replace')
        
        time.sleep(0.001)


def test_sync_upload(ser, base_addr, num_words):
    """Test upload with synchronous flow control."""
    print(f"\n{'='*70}")
    print(f"Testing synchronous upload: {num_words} words ({num_words*4} bytes)")
    print(f"{'='*70}")
    
    # Generate test data
    test_data = [random.randint(0, 0xFFFFFFFF) for _ in range(num_words)]
    
    # Upload phase
    print("Uploading with synchronous flow control...")
    start = time.time()
    
    for i, value in enumerate(test_data):
        addr = base_addr + (i * 4)
        cmd = f'mem_write 0x{addr:08x} 0x{value:08x}'
        
        # Wait for prompt after each command
        response = send_command_sync(ser, cmd, timeout=2.0)
        
        # Check for errors
        if 'error' in response.lower() or 'fail' in response.lower():
            print(f"  ERROR in response: {response[:100]}")
        
        # Progress
        if i % 64 == 0:
            print(f"  {i}/{num_words} words...")
    
    elapsed = time.time() - start
    rate = (num_words * 4) / elapsed
    print(f"Upload complete: {elapsed:.1f}s ({rate:.0f} B/s)")
    
    # Verification phase
    print("\nVerifying...")
    errors = 0
    sample_size = min(32, num_words)
    sample_indices = random.sample(range(num_words), sample_size)
    
    for i in sample_indices:
        addr = base_addr + (i * 4)
        expected = test_data[i]
        
        # Read back using synchronous method
        response = send_command_sync(ser, f'mem_read 0x{addr:08x} 4', timeout=1.0)
        
        # Parse response
        actual = None
        for line in response.split('\n'):
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
            if errors <= 5:
                print(f"  ✗ ERROR at 0x{addr:08X}: expected 0x{expected:08X}, got {actual}")
    
    if errors == 0:
        print(f"  ✓ ALL {sample_size} samples verified OK")
        return True
    else:
        print(f"  ✗ {errors}/{sample_size} errors")
        return False


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', default='/dev/ttyUSB0')
    args = parser.parse_args()
    
    print(f"Connecting to {args.port}...")
    ser = serial.Serial(args.port, 115200, timeout=2)
    time.sleep(0.1)
    
    # Initialize - ensure we're at a prompt
    ser.reset_input_buffer()
    ser.write(b'\r\n')
    time.sleep(0.2)
    response = ser.read(ser.in_waiting).decode('utf-8', errors='replace')
    print(f"Initial response: {response}")
    
    # Check for prompt - it has ANSI escape codes
    if 'litex' not in response:
        print("WARNING: BIOS prompt not detected. FPGA may need reprogramming.")
        print("Run: python3 terasic_de10lite_custom.py --build --load")
        return
    
    print("\n" + "="*70)
    print("SYNCHRONOUS UPLOAD TEST")
    print("="*70)
    print("Using flow control: waiting for 'litex>' prompt after each command")
    
    tests = [
        (0x40000000, 256, "1KB block"),
        (0x40001000, 512, "2KB block"),
        (0x40002000, 1024, "4KB block"),
    ]
    
    results = []
    
    try:
        for base_addr, num_words, desc in tests:
            success = test_sync_upload(ser, base_addr, num_words)
            results.append((desc, success))
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


if __name__ == '__main__':
    main()
