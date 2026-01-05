#!/usr/bin/env python3
"""
Fast NES ROM loader using batched mem_write commands.

Uses BIOS mem_write commands with minimal delays for reliable upload.
"""

import serial
import time
import struct
import argparse
from pathlib import Path


def send_command_sync(ser, cmd: str, timeout: float = 1.0) -> str:
    """Send command and wait for BIOS prompt - ensures synchronous execution.
    
    This implements proper flow control by waiting for the 'litex>' prompt
    after each command, guaranteeing the BIOS has completed processing
    before sending the next command. No blind delays needed.
    """
    ser.write(cmd.encode() + b'\r\n')
    
    # Read until we see the prompt - this proves BIOS finished
    response = b''
    start = time.time()
    while True:
        if ser.in_waiting > 0:
            chunk = ser.read(ser.in_waiting)
            response += chunk
            # Check for prompt (handles ANSI escape codes: \x1b[92;1mlitex\x1b[0m>)
            if b'litex' in response and b'>' in response:
                return response.decode('utf-8', errors='replace')
        
        # Timeout check
        if time.time() - start > timeout:
            return response.decode('utf-8', errors='replace')
        
        time.sleep(0.001)  # Small delay to avoid busy-waiting


def upload_to_sdram(ser, data: bytes, base_address: int, name: str = "data"):
    """Upload binary data to SDRAM using mem_write commands with synchronous flow control."""
    
    # Ensure we're aligned to 4 bytes
    if len(data) % 4 != 0:
        data = data + bytes(4 - len(data) % 4)
    
    total = len(data)
    sent = 0
    errors = 0
    
    print(f'Uploading {name}: {total} bytes to 0x{base_address:08X}')
    print('  Using synchronous flow control (waiting for prompt after each write)')
    start_time = time.time()
    last_progress = 0
    
    # Clear any pending data and ensure we're at a prompt
    ser.reset_input_buffer()
    ser.write(b'\r\n')
    time.sleep(0.1)
    ser.read(ser.in_waiting)
    
    while sent < total:
        # Write 4 bytes at a time
        addr = base_address + sent
        val = struct.unpack('<I', data[sent:sent+4])[0]  # Little endian
        
        cmd = f'mem_write 0x{addr:08x} 0x{val:08x}'
        
        # Send command and wait for prompt - NO BLIND DELAYS!
        response = send_command_sync(ser, cmd, timeout=2.0)
        
        # Check for errors in response
        if 'error' in response.lower() or 'fail' in response.lower():
            errors += 1
            if errors <= 5:  # Only print first few errors
                print(f'  Error at 0x{addr:08X}: {response[:100]}')
        
        sent += 4
        
        # Progress update
        progress = sent * 100 // total
        if progress >= last_progress + 5:
            elapsed = time.time() - start_time
            rate = sent / elapsed if elapsed > 0 else 0
            remaining = (total - sent) / rate if rate > 0 else 0
            print(f'  {sent}/{total} bytes ({progress}%) - {rate:.0f} B/s, ETA {remaining:.0f}s')
            last_progress = progress
    
    elapsed = time.time() - start_time
    rate = total / elapsed if elapsed > 0 else 0
    print(f'  Done: {total} bytes in {elapsed:.1f}s ({rate:.0f} B/s)')
    
    if errors > 0:
        print(f'  Warning: {errors} errors during upload')
    
    return errors == 0


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


def upload_to_sdram(ser, data: bytes, base_address: int, name: str = "data"):
    """Upload binary data to SDRAM using mem_write commands."""
    
    # Ensure we're aligned to 4 bytes
    if len(data) % 4 != 0:
        data = data + bytes(4 - len(data) % 4)
    
    total = len(data)
    sent = 0
    errors = 0
    
    print(f'Uploading {name}: {total} bytes to 0x{base_address:08X}')
    start_time = time.time()
    last_progress = 0
    
    # Clear any pending data
    ser.reset_input_buffer()
    
    while sent < total:
        # Write 4 bytes at a time
        addr = base_address + sent
        val = struct.unpack('<I', data[sent:sent+4])[0]  # Little endian
        
        cmd = f'mem_write 0x{addr:08x} 0x{val:08x}\r\n'
        ser.write(cmd.encode())
        
        # Wait for command to be processed (10ms is reliable)
        time.sleep(0.010)
        
        # Read and discard response every few commands
        if sent % 64 == 0 and ser.in_waiting > 0:
            ser.read(ser.in_waiting)
        
        sent += 4
        
        # Progress update
        progress = sent * 100 // total
        if progress >= last_progress + 5:
            elapsed = time.time() - start_time
            rate = sent / elapsed if elapsed > 0 else 0
            remaining = (total - sent) / rate if rate > 0 else 0
            print(f'  {sent}/{total} bytes ({progress}%) - {rate:.0f} B/s, ETA {remaining:.0f}s')
            last_progress = progress
    
    # Final cleanup
    time.sleep(0.1)
    ser.read(ser.in_waiting)
    
    elapsed = time.time() - start_time
    rate = total / elapsed if elapsed > 0 else 0
    print(f'  Done: {total} bytes in {elapsed:.1f}s ({rate:.0f} B/s)')
    
    return errors == 0


def verify_sdram(ser, data: bytes, base_address: int, samples: int = 16):
    """Verify random samples from uploaded data."""
    import random
    
    errors = 0
    checks = min(samples, len(data) // 4)
    
    # Pick random offsets to check
    offsets = random.sample(range(0, len(data), 4), checks)
    
    print(f'Verifying {checks} samples...')
    
    for i, offset in enumerate(offsets):
        addr = base_address + offset
        expected = struct.unpack('<I', data[offset:offset+4])[0]
        
        # Read back
        ser.reset_input_buffer()
        ser.write(f'mem_read 0x{addr:08x} 4\r\n'.encode())
        time.sleep(0.05)
        resp = ser.read(1024).decode('utf-8', errors='replace')
        
        # Parse response
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
            print(f'  ERROR at 0x{addr:08X}: expected 0x{expected:08X}, got {actual}')
    
    if errors == 0:
        print(f'  All {checks} samples verified OK')
    else:
        print(f'  {errors}/{checks} errors')
    
    return errors == 0


def main():
    parser = argparse.ArgumentParser(description='Upload NES ROM to SDRAM')
    parser.add_argument('rom', help='NES ROM file (.nes)')
    parser.add_argument('--port', default='/dev/ttyUSB0', help='Serial port')
    parser.add_argument('--no-verify', action='store_true', help='Skip verification')
    parser.add_argument('--prg-only', action='store_true', help='Only upload PRG ROM')
    args = parser.parse_args()
    
    # Memory addresses
    PRG_ROM_BASE = 0x40000000
    CHR_ROM_BASE = 0x40080000
    
    # Read ROM
    rom_path = Path(args.rom)
    if not rom_path.exists():
        print(f"Error: File not found: {args.rom}")
        return 1
    
    with open(args.rom, 'rb') as f:
        rom_data = f.read()
    
    # Parse header
    try:
        info = parse_nes_header(rom_data)
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    
    print(f"\nNES ROM: {args.rom}")
    print(f"  PRG-ROM: {info['prg_size'] // 1024}KB ({info['prg_banks']} banks)")
    print(f"  CHR-ROM: {info['chr_size'] // 1024}KB ({info['chr_banks']} banks)")
    print(f"  Mapper:  {info['mapper']}")
    print()
    
    # Extract ROM data
    header_size = 16
    trainer_size = 512 if info['has_trainer'] else 0
    prg_offset = header_size + trainer_size
    chr_offset = prg_offset + info['prg_size']
    
    prg_data = rom_data[prg_offset:prg_offset + info['prg_size']]
    chr_data = rom_data[chr_offset:chr_offset + info['chr_size']] if info['chr_size'] > 0 else b''
    
    # Mirror 16KB PRG to 32KB for NROM-128
    if len(prg_data) == 16384:
        prg_data = prg_data + prg_data
        print(f"  Note: Mirrored 16KB PRG to 32KB")
    
    # Connect to BIOS
    print(f"Connecting to {args.port}...")
    ser = serial.Serial(args.port, 115200, timeout=2.0)
    time.sleep(0.5)
    
    # Get BIOS prompt
    ser.reset_input_buffer()
    ser.write(b'\r\n')
    time.sleep(0.3)
    resp = ser.read(1024)
    if b'litex' not in resp.lower():
        print("Warning: BIOS prompt not detected")
    
    # Upload PRG ROM
    print()
    upload_to_sdram(ser, prg_data, PRG_ROM_BASE, "PRG-ROM")
    
    # Upload CHR ROM
    if chr_data and not args.prg_only:
        print()
        upload_to_sdram(ser, chr_data, CHR_ROM_BASE, "CHR-ROM")
    
    # Verify
    if not args.no_verify:
        print()
        verify_sdram(ser, prg_data, PRG_ROM_BASE, 16)
        if chr_data and not args.prg_only:
            verify_sdram(ser, chr_data, CHR_ROM_BASE, 8)
    
    ser.close()
    print("\nUpload complete!")
    return 0


if __name__ == '__main__':
    exit(main())
