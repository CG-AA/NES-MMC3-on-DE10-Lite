#!/usr/bin/env python3
"""
NES ROM Loader for DE10-Lite via UART

Uploads NES ROM data to SDRAM via LiteX BIOS commands.

Usage:
    python3 nes_rom_loader.py <rom.nes> [--port /dev/ttyUSB0] [--verify]

Memory Layout in SDRAM:
    0x40000000: PRG-ROM (up to 512KB)
    0x40080000: CHR-ROM (up to 256KB) - optional, typically in BRAM
"""

import argparse
import serial
import sys
import time
from pathlib import Path


# SDRAM base addresses
PRG_ROM_BASE = 0x40000000
CHR_ROM_BASE = 0x40080000


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
        'prg_size': prg_banks * 16384,  # 16KB units
        'chr_size': chr_banks * 8192,    # 8KB units
        'mapper': (flags6 >> 4) | (flags7 & 0xF0),
        'mirroring': 'vertical' if (flags6 & 1) else 'horizontal',
        'has_battery': bool(flags6 & 2),
        'has_trainer': bool(flags6 & 4),
        'prg_banks': prg_banks,
        'chr_banks': chr_banks,
    }


def send_command(ser: serial.Serial, cmd: str, timeout: float = 0.1) -> str:
    """Send command and return response."""
    ser.reset_input_buffer()
    ser.write((cmd + '\r\n').encode())
    time.sleep(timeout)
    return ser.read(4096).decode('utf-8', errors='replace')


def write_word(ser: serial.Serial, addr: int, value: int) -> bool:
    """Write a 32-bit word to memory."""
    cmd = f'mem_write 0x{addr:08x} 0x{value:08x}'
    resp = send_command(ser, cmd, timeout=0.005)
    return 'litex>' in resp


def read_word(ser: serial.Serial, addr: int) -> int:
    """Read a 32-bit word from memory."""
    cmd = f'mem_read 0x{addr:08x} 4'
    resp = send_command(ser, cmd, timeout=0.01)
    
    # Parse response like "0x40000000  78 56 34 12"
    for line in resp.split('\n'):
        if f'0x{addr:08x}' in line.lower():
            parts = line.split()
            if len(parts) >= 5:
                try:
                    # Bytes are in little-endian order
                    b0 = int(parts[1], 16)
                    b1 = int(parts[2], 16)
                    b2 = int(parts[3], 16)
                    b3 = int(parts[4], 16)
                    return b0 | (b1 << 8) | (b2 << 16) | (b3 << 24)
                except (ValueError, IndexError):
                    pass
    return None


def upload_data(ser: serial.Serial, base_addr: int, data: bytes, 
                name: str = "data", verify: bool = False) -> bool:
    """Upload data to SDRAM in 32-bit words."""
    
    # Pad to 4-byte boundary
    padded = data + bytes((4 - len(data) % 4) % 4)
    total_words = len(padded) // 4
    
    print(f"Uploading {name}: {len(data)} bytes ({total_words} words) to 0x{base_addr:08X}")
    
    errors = 0
    start_time = time.time()
    
    for i in range(total_words):
        offset = i * 4
        addr = base_addr + offset
        
        # Pack 4 bytes as little-endian word
        word = (padded[offset] | 
                (padded[offset + 1] << 8) | 
                (padded[offset + 2] << 16) | 
                (padded[offset + 3] << 24))
        
        if not write_word(ser, addr, word):
            errors += 1
            if errors <= 5:
                print(f"  Write error at 0x{addr:08X}")
        
        # Progress indicator
        if (i + 1) % 1000 == 0 or i == total_words - 1:
            pct = (i + 1) * 100 // total_words
            elapsed = time.time() - start_time
            rate = (i + 1) * 4 / elapsed if elapsed > 0 else 0
            print(f"  {i + 1}/{total_words} words ({pct}%) - {rate:.0f} bytes/sec", end='\r')
    
    print()
    elapsed = time.time() - start_time
    rate = len(padded) / elapsed if elapsed > 0 else 0
    print(f"  Upload complete in {elapsed:.1f}s ({rate:.0f} bytes/sec)")
    
    # Verify if requested
    if verify:
        print(f"  Verifying {name}...")
        verify_errors = 0
        
        for i in range(min(total_words, 100)):  # Verify first 100 words
            offset = i * 4
            addr = base_addr + offset
            
            expected = (padded[offset] | 
                       (padded[offset + 1] << 8) | 
                       (padded[offset + 2] << 16) | 
                       (padded[offset + 3] << 24))
            
            actual = read_word(ser, addr)
            
            if actual != expected:
                verify_errors += 1
                if verify_errors <= 5:
                    print(f"  Verify error at 0x{addr:08X}: expected 0x{expected:08X}, got 0x{actual:08X}")
        
        if verify_errors == 0:
            print(f"  Verification passed (checked {min(total_words, 100)} words)")
        else:
            print(f"  Verification FAILED: {verify_errors} errors")
            return False
    
    return errors == 0


def load_nes_rom(filename: str, port: str = '/dev/ttyUSB0', 
                 baudrate: int = 115200, verify: bool = False,
                 upload_chr: bool = False) -> bool:
    """Load NES ROM to SDRAM via UART."""
    
    # Read ROM file
    rom_path = Path(filename)
    if not rom_path.exists():
        print(f"Error: File not found: {filename}")
        return False
    
    with open(filename, 'rb') as f:
        rom_data = f.read()
    
    # Parse header
    try:
        info = parse_nes_header(rom_data)
    except ValueError as e:
        print(f"Error: {e}")
        return False
    
    print(f"\n{'='*60}")
    print(f"NES ROM: {filename}")
    print(f"{'='*60}")
    print(f"  PRG-ROM: {info['prg_size'] // 1024}KB ({info['prg_banks']} banks)")
    print(f"  CHR-ROM: {info['chr_size'] // 1024}KB ({info['chr_banks']} banks)")
    print(f"  Mapper:  {info['mapper']}")
    print(f"  Mirror:  {info['mirroring']}")
    print(f"  Battery: {info['has_battery']}")
    print()
    
    # Warn about mapper
    if info['mapper'] != 0:
        print(f"WARNING: Mapper {info['mapper']} - only NROM (0) fully supported")
    
    # Calculate offsets
    header_size = 16
    trainer_size = 512 if info['has_trainer'] else 0
    prg_offset = header_size + trainer_size
    chr_offset = prg_offset + info['prg_size']
    
    # Extract ROM data
    prg_data = rom_data[prg_offset:prg_offset + info['prg_size']]
    chr_data = rom_data[chr_offset:chr_offset + info['chr_size']]
    
    # For 16KB PRG (NROM-128), mirror to 32KB
    if len(prg_data) == 16384:
        print("  Mirroring 16KB PRG to 32KB (NROM-128)")
        prg_data = prg_data + prg_data
    
    # Connect to serial
    print(f"Connecting to {port} at {baudrate} baud...")
    try:
        ser = serial.Serial(port, baudrate, timeout=2)
        time.sleep(0.5)
    except serial.SerialException as e:
        print(f"Error opening serial port: {e}")
        return False
    
    # Clear buffer and check connection
    ser.reset_input_buffer()
    resp = send_command(ser, '', timeout=0.3)
    if 'litex>' not in resp:
        print("Warning: No LiteX prompt detected. Trying anyway...")
    else:
        print("Connected to LiteX BIOS")
    
    # Upload PRG-ROM
    print()
    success = upload_data(ser, PRG_ROM_BASE, prg_data, "PRG-ROM", verify=verify)
    
    if not success:
        print("PRG-ROM upload failed!")
        ser.close()
        return False
    
    # Upload CHR-ROM if requested and present
    if upload_chr and info['chr_size'] > 0:
        print()
        success = upload_data(ser, CHR_ROM_BASE, chr_data, "CHR-ROM", verify=verify)
        if not success:
            print("CHR-ROM upload failed!")
            ser.close()
            return False
    elif info['chr_size'] > 0:
        print(f"\nNote: CHR-ROM ({info['chr_size']//1024}KB) not uploaded (use --chr to include)")
    else:
        print("\nNote: Game uses CHR-RAM (no CHR-ROM to upload)")
    
    ser.close()
    
    print()
    print("="*60)
    print("ROM upload complete!")
    print(f"  PRG-ROM at 0x{PRG_ROM_BASE:08X} ({len(prg_data)} bytes)")
    if upload_chr and info['chr_size'] > 0:
        print(f"  CHR-ROM at 0x{CHR_ROM_BASE:08X} ({len(chr_data)} bytes)")
    print("="*60)
    
    return True


def main():
    parser = argparse.ArgumentParser(description='Upload NES ROM to DE10-Lite SDRAM')
    parser.add_argument('rom', help='NES ROM file (.nes)')
    parser.add_argument('--port', '-p', default='/dev/ttyUSB0', 
                        help='Serial port (default: /dev/ttyUSB0)')
    parser.add_argument('--baud', '-b', type=int, default=115200,
                        help='Baud rate (default: 115200)')
    parser.add_argument('--verify', '-v', action='store_true',
                        help='Verify uploaded data')
    parser.add_argument('--chr', action='store_true',
                        help='Also upload CHR-ROM to SDRAM')
    
    args = parser.parse_args()
    
    success = load_nes_rom(args.rom, args.port, args.baud, 
                           verify=args.verify, upload_chr=args.chr)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
