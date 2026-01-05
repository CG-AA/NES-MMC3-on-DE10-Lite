#!/usr/bin/env python3
"""
NES ROM Uploader using BIOS Manager

Reliable ROM upload with auto-recovery and progress tracking.
"""

import sys
import time
import struct
import random
from pathlib import Path

from bios_manager import BIOSConnection


def parse_nes_header(data: bytes) -> dict:
    """Parse iNES header and return ROM info."""
    if len(data) < 16:
        raise ValueError("File too small for NES header")
    
    if data[0:4] != b'NES\x1a':
        raise ValueError("Not a valid NES file (missing NES header)")
    
    prg_banks = data[4]
    chr_banks = data[5]
    flags6 = data[6]
    flags7 = data[7]
    
    return {
        'prg_size': prg_banks * 16384,
        'chr_size': chr_banks * 8192,
        'mapper': (flags6 >> 4) | (flags7 & 0xF0),
        'mirroring': 'vertical' if (flags6 & 1) else 'horizontal',
        'has_trainer': bool(flags6 & 4),
        'prg_banks': prg_banks,
        'chr_banks': chr_banks,
    }


def upload_data(bios, data: bytes, base_address: int, name: str, delay_ms: int = 10):
    """Upload binary data to SDRAM with progress tracking."""
    
    # Pad to 4-byte alignment
    if len(data) % 4 != 0:
        data = data + bytes(4 - len(data) % 4)
    
    total = len(data)
    num_words = total // 4
    
    print(f'Uploading {name}: {total} bytes to 0x{base_address:08X}')
    
    start_time = time.time()
    last_progress = -1
    
    for i in range(num_words):
        addr = base_address + (i * 4)
        val = struct.unpack('<I', data[i*4:(i+1)*4])[0]
        
        bios.mem_write(addr, val, delay=delay_ms/1000.0)
        
        # Progress update every 5%
        progress = (i + 1) * 100 // num_words
        if progress >= last_progress + 5:
            elapsed = time.time() - start_time
            rate = (i + 1) * 4 / elapsed if elapsed > 0 else 0
            remaining = (num_words - i - 1) * 4 / rate if rate > 0 else 0
            print(f'  {progress}% ({(i+1)*4}/{total} bytes) - {rate:.0f} B/s, ETA {remaining:.0f}s')
            last_progress = progress
    
    # Final flush
    time.sleep(0.2)
    if bios.ser.in_waiting:
        bios.ser.read(bios.ser.in_waiting)
    
    elapsed = time.time() - start_time
    rate = total / elapsed if elapsed > 0 else 0
    print(f'  Done: {total} bytes in {elapsed:.1f}s ({rate:.0f} B/s)')
    
    return True


def verify_data(bios, data: bytes, base_address: int, name: str, samples: int = 32):
    """Verify uploaded data by sampling random addresses."""
    
    if len(data) % 4 != 0:
        data = data + bytes(4 - len(data) % 4)
    
    num_words = len(data) // 4
    sample_count = min(samples, num_words)
    
    print(f'Verifying {name}: {sample_count} samples...')
    
    # Sample random offsets
    indices = sorted(random.sample(range(num_words), sample_count))
    
    errors = 0
    for i in indices:
        addr = base_address + (i * 4)
        expected = struct.unpack('<I', data[i*4:(i+1)*4])[0]
        
        actual = bios.mem_read(addr)
        
        if actual != expected:
            errors += 1
            if errors <= 5:
                actual_str = f"0x{actual:08X}" if actual is not None else "None"
                print(f'  ERROR at 0x{addr:08X}: expected 0x{expected:08X}, got {actual_str}')
    
    if errors == 0:
        print(f'  ✓ All {sample_count} samples verified OK')
        return True
    else:
        print(f'  ✗ {errors}/{sample_count} errors')
        return False


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Upload NES ROM to SDRAM')
    parser.add_argument('rom', help='NES ROM file (.nes)')
    parser.add_argument('--port', default='/dev/ttyUSB0', help='Serial port')
    parser.add_argument('--delay', type=int, default=10, help='Delay between writes (ms)')
    parser.add_argument('--no-verify', action='store_true', help='Skip verification')
    parser.add_argument('--prg-only', action='store_true', help='Only upload PRG ROM')
    args = parser.parse_args()
    
    # Memory addresses
    PRG_ROM_BASE = 0x40000000
    CHR_ROM_BASE = 0x40080000
    
    # Read ROM file
    rom_path = Path(args.rom)
    if not rom_path.exists():
        print(f"ERROR: ROM file not found: {args.rom}")
        sys.exit(1)
    
    rom_data = rom_path.read_bytes()
    
    # Parse header
    try:
        info = parse_nes_header(rom_data)
    except ValueError as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    
    print("="*70)
    print(f"NES ROM: {rom_path.name}")
    print("="*70)
    print(f"  Mapper: {info['mapper']}")
    print(f"  PRG-ROM: {info['prg_size']//1024}KB ({info['prg_banks']} banks)")
    print(f"  CHR-ROM: {info['chr_size']//1024}KB ({info['chr_banks']} banks)")
    print(f"  Mirroring: {info['mirroring']}")
    print()
    
    # Check mapper
    if info['mapper'] != 0:
        print(f"WARNING: Mapper {info['mapper']} not fully supported (only NROM/0 tested)")
    
    # Extract ROM data
    header_size = 16 + (512 if info['has_trainer'] else 0)
    prg_data = rom_data[header_size:header_size + info['prg_size']]
    chr_data = rom_data[header_size + info['prg_size']:header_size + info['prg_size'] + info['chr_size']]
    
    # Connect to BIOS
    bios = BIOSConnection(port=args.port)
    
    if not bios.ensure_bios():
        print("ERROR: Could not connect to BIOS")
        sys.exit(1)
    
    print()
    
    # Upload PRG-ROM
    if not upload_data(bios, prg_data, PRG_ROM_BASE, "PRG-ROM", args.delay):
        print("ERROR: PRG-ROM upload failed")
        bios.close()
        sys.exit(1)
    
    # Verify PRG-ROM
    if not args.no_verify:
        if not verify_data(bios, prg_data, PRG_ROM_BASE, "PRG-ROM"):
            print("ERROR: PRG-ROM verification failed")
            bios.close()
            sys.exit(1)
    
    # Upload CHR-ROM (if present and not skipped)
    if not args.prg_only and info['chr_size'] > 0:
        print()
        if not upload_data(bios, chr_data, CHR_ROM_BASE, "CHR-ROM", args.delay):
            print("ERROR: CHR-ROM upload failed")
            bios.close()
            sys.exit(1)
        
        if not args.no_verify:
            if not verify_data(bios, chr_data, CHR_ROM_BASE, "CHR-ROM"):
                print("ERROR: CHR-ROM verification failed")
                bios.close()
                sys.exit(1)
    
    bios.close()
    
    print()
    print("="*70)
    print("✅ ROM UPLOAD COMPLETE!")
    print("="*70)
    print(f"  PRG-ROM: 0x{PRG_ROM_BASE:08X} - 0x{PRG_ROM_BASE + len(prg_data):08X}")
    if info['chr_size'] > 0 and not args.prg_only:
        print(f"  CHR-ROM: 0x{CHR_ROM_BASE:08X} - 0x{CHR_ROM_BASE + len(chr_data):08X}")


if __name__ == '__main__':
    main()
