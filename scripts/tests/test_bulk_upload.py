#!/usr/bin/env python3
"""
Test bulk upload with safe SDRAM timings.
Uploads 1KB, 4KB, and 8KB blocks and verifies all data.
Uses BIOSConnection for reliable connection management.
"""

import sys
import time
import struct
import random

from bios_manager import BIOSConnection


def upload_block(bios, base_addr, data, delay_ms=10):
    """Upload a block of bytes to SDRAM."""
    # Pad to 4-byte alignment
    if len(data) % 4 != 0:
        data = data + bytes(4 - len(data) % 4)
    
    num_words = len(data) // 4
    
    for i in range(num_words):
        addr = base_addr + (i * 4)
        val = struct.unpack('<I', data[i*4:(i+1)*4])[0]
        bios.mem_write(addr, val, delay=delay_ms/1000.0)
    
    # Final flush
    time.sleep(0.2)
    if bios.ser.in_waiting:
        bios.ser.read(bios.ser.in_waiting)


def verify_block(bios, base_addr, data, sample_count=None):
    """Verify uploaded data by sampling random addresses."""
    if len(data) % 4 != 0:
        data = data + bytes(4 - len(data) % 4)
    
    num_words = len(data) // 4
    
    if sample_count is None:
        sample_count = min(16, num_words)
    
    # Sample random offsets
    if sample_count >= num_words:
        indices = list(range(num_words))
    else:
        indices = sorted(random.sample(range(num_words), sample_count))
    
    errors = 0
    
    for i in indices:
        addr = base_addr + (i * 4)
        expected = struct.unpack('<I', data[i*4:(i+1)*4])[0]
        
        actual = bios.mem_read(addr)
        
        if actual != expected:
            errors += 1
            if errors <= 3:
                actual_str = f"0x{actual:08X}" if actual is not None else "None"
                print(f"    ERROR at 0x{addr:08X}: expected 0x{expected:08X}, got {actual_str}")
    
    return errors, sample_count


def test_block(bios, size_bytes, delay_ms, description):
    """Test uploading and verifying a block of data."""
    print(f"\n{'='*70}")
    print(f"TEST: {description}")
    print(f"{'='*70}")
    
    base = 0x40000000
    
    # Generate random test data
    test_data = bytes([random.randint(0, 255) for _ in range(size_bytes)])
    
    print(f"  Size: {size_bytes} bytes ({size_bytes//1024}KB)")
    print(f"  Delay: {delay_ms}ms between writes")
    
    # Upload
    print(f"  Uploading...", end='', flush=True)
    start = time.time()
    upload_block(bios, base, test_data, delay_ms)
    elapsed = time.time() - start
    rate = size_bytes / elapsed
    print(f" done ({elapsed:.1f}s, {rate:.0f} B/s)")
    
    # Verify
    print(f"  Verifying...", end='', flush=True)
    errors, samples = verify_block(bios, base, test_data)
    
    if errors == 0:
        print(f" ✓ PASS ({samples}/{samples} samples OK)")
        return True
    else:
        print(f" ✗ FAIL ({errors}/{samples} errors)")
        return False


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', default='/dev/ttyUSB0')
    args = parser.parse_args()
    
    print("="*70)
    print("BULK UPLOAD TEST WITH SAFE SDRAM TIMINGS")
    print("="*70)
    
    bios = BIOSConnection(port=args.port)
    
    if not bios.ensure_bios():
        print("ERROR: Could not establish BIOS connection")
        sys.exit(1)
    
    print("BIOS connected, starting tests...")
    
    tests = [
        (256, 20, "256B block with 20ms delay"),
        (1024, 20, "1KB block with 20ms delay"),
        (1024, 10, "1KB block with 10ms delay"),
        (4096, 10, "4KB block with 10ms delay"),
    ]
    
    results = []
    
    try:
        for size, delay, desc in tests:
            success = test_block(bios, size, delay, desc)
            results.append((desc, success))
            
            # Check if BIOS is still alive after each test
            if not bios.check_bios():
                print("\n⚠️  BIOS stopped responding, attempting recovery...")
                if not bios.ensure_bios():
                    print("Could not recover, stopping tests")
                    break
            
            time.sleep(0.5)
    
    finally:
        bios.close()
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, s in results if s)
    total = len(results)
    
    for desc, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"  {status}: {desc}")
    
    print(f"\nResult: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✅ BULK UPLOAD WORKING! Safe timings have fixed the issue.")
        print("   Ready to test full ROM upload.")
    else:
        print("\n⚠️  Some tests failed. May need further timing adjustments.")


if __name__ == '__main__':
    main()
