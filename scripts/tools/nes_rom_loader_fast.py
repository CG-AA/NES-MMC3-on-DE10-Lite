#!/usr/bin/env python3
"""
Fast NES ROM Loader for DE10-Lite

Uses LiteX remote client for fast memory access (vs slow UART mem_write).

Usage:
    # First, start litex_server in another terminal:
    #   litex_server --uart --uart-port /dev/ttyUSB0 --uart-baudrate 115200
    
    # Then run:
    python3 nes_rom_loader_fast.py <rom.nes>

Memory Layout in SDRAM:
    0x40000000: PRG-ROM (up to 512KB)
    0x40080000: CHR-ROM (up to 256KB)
"""

import argparse
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
        'chr_size': chr_banks * 8192,   # 8KB units
        'mapper': (flags6 >> 4) | (flags7 & 0xF0),
        'mirroring': 'vertical' if (flags6 & 1) else 'horizontal',
        'has_battery': bool(flags6 & 2),
        'has_trainer': bool(flags6 & 4),
        'prg_banks': prg_banks,
        'chr_banks': chr_banks,
    }


def upload_with_litex_client(base_addr: int, data: bytes, name: str = "data") -> bool:
    """Upload data using LiteX RemoteClient (fast)."""
    try:
        from litex import RemoteClient
    except ImportError:
        print("Error: litex not installed. Run: pip install litex")
        return False
    
    print(f"Connecting to LiteX server...")
    try:
        bus = RemoteClient()
        bus.open()
    except Exception as e:
        print(f"Error connecting to LiteX server: {e}")
        print("Make sure litex_server is running:")
        print("  litex_server --uart --uart-port /dev/ttyUSB0")
        return False
    
    print(f"Uploading {name}: {len(data)} bytes to 0x{base_addr:08X}")
    
    # Pad to 4-byte boundary
    padded = data + bytes((4 - len(data) % 4) % 4)
    
    start_time = time.time()
    
    # Write in chunks of 256 words (1KB) for efficiency
    chunk_words = 256
    chunk_bytes = chunk_words * 4
    total_bytes = len(padded)
    
    for offset in range(0, total_bytes, chunk_bytes):
        chunk = padded[offset:offset + chunk_bytes]
        addr = base_addr + offset
        
        # Convert to list of 32-bit words
        words = []
        for i in range(0, len(chunk), 4):
            if i + 3 < len(chunk):
                word = (chunk[i] | (chunk[i+1] << 8) | 
                       (chunk[i+2] << 16) | (chunk[i+3] << 24))
                words.append(word)
        
        # Write words
        for i, word in enumerate(words):
            bus.write(addr + i * 4, word)
        
        # Progress
        pct = (offset + len(chunk)) * 100 // total_bytes
        elapsed = time.time() - start_time
        rate = (offset + len(chunk)) / elapsed if elapsed > 0 else 0
        print(f"  {offset + len(chunk)}/{total_bytes} bytes ({pct}%) - {rate/1024:.1f} KB/s", end='\r')
    
    print()
    
    elapsed = time.time() - start_time
    rate = total_bytes / elapsed if elapsed > 0 else 0
    print(f"  Upload complete in {elapsed:.1f}s ({rate/1024:.1f} KB/s)")
    
    bus.close()
    return True


def upload_with_uart_fast(base_addr: int, data: bytes, name: str = "data",
                          port: str = '/dev/ttyUSB0', baudrate: int = 115200) -> bool:
    """Upload using UART - reliable but slow."""
    import serial
    
    print(f"Uploading {name}: {len(data)} bytes to 0x{base_addr:08X} via UART")
    print(f"  Estimated time: ~{len(data) // 300}s (UART is slow)")
    
    ser = serial.Serial(port, baudrate, timeout=1.0)
    time.sleep(0.5)
    
    # Clear buffer
    ser.reset_input_buffer()
    ser.write(b'\r\n')
    time.sleep(0.2)
    ser.read(4096)
    
    # Pad to 4-byte boundary
    padded = data + bytes((4 - len(data) % 4) % 4)
    total_words = len(padded) // 4
    
    start_time = time.time()
    
    for i in range(total_words):
        offset = i * 4
        addr = base_addr + offset
        
        word = (padded[offset] | (padded[offset + 1] << 8) | 
                (padded[offset + 2] << 16) | (padded[offset + 3] << 24))
        
        # Send command and wait for prompt
        cmd = f'mem_write 0x{addr:08x} 0x{word:08x}\r\n'
        ser.write(cmd.encode())
        
        # Wait for echo + response (every word)
        time.sleep(0.001)  # 1ms delay
        
        # Drain buffer periodically
        if (i + 1) % 20 == 0:
            ser.read(2048)
        
        # Progress
        if (i + 1) % 200 == 0 or i == total_words - 1:
            pct = (i + 1) * 100 // total_words
            elapsed = time.time() - start_time
            rate = (i + 1) * 4 / elapsed if elapsed > 0 else 0
            eta = (total_words - i - 1) * 4 / rate if rate > 0 else 0
            print(f"  {(i + 1) * 4}/{len(padded)} bytes ({pct}%) - {rate:.0f} B/s, ETA {eta:.0f}s", end='\r')
    
    # Final drain
    time.sleep(0.2)
    ser.read(4096)
    
    print()
    elapsed = time.time() - start_time
    rate = len(padded) / elapsed if elapsed > 0 else 0
    print(f"  Upload complete in {elapsed:.1f}s ({rate:.0f} bytes/sec)")
    
    ser.close()
    return True


def verify_data(base_addr: int, data: bytes, name: str = "data",
                port: str = '/dev/ttyUSB0', baudrate: int = 115200,
                sample_count: int = 20) -> bool:
    """Verify uploaded data by sampling random locations."""
    import serial
    import random
    
    print(f"Verifying {name} ({sample_count} samples)...")
    
    ser = serial.Serial(port, baudrate, timeout=0.5)
    time.sleep(0.3)
    ser.reset_input_buffer()
    
    # Pad for alignment
    padded = data + bytes((4 - len(data) % 4) % 4)
    total_words = len(padded) // 4
    
    # Sample random locations
    errors = 0
    samples = random.sample(range(total_words), min(sample_count, total_words))
    
    for i in samples:
        offset = i * 4
        addr = base_addr + offset
        
        expected = (padded[offset] | (padded[offset + 1] << 8) | 
                   (padded[offset + 2] << 16) | (padded[offset + 3] << 24))
        
        # Read
        ser.write(f'mem_read 0x{addr:08x} 4\r\n'.encode())
        time.sleep(0.02)
        resp = ser.read(1024).decode('utf-8', errors='replace')
        
        # Parse response
        actual = None
        for line in resp.split('\n'):
            if f'0x{addr:08x}' in line.lower():
                parts = line.split()
                if len(parts) >= 5:
                    try:
                        b0 = int(parts[1], 16)
                        b1 = int(parts[2], 16)
                        b2 = int(parts[3], 16)
                        b3 = int(parts[4], 16)
                        actual = b0 | (b1 << 8) | (b2 << 16) | (b3 << 24)
                    except (ValueError, IndexError):
                        pass
        
        if actual != expected:
            errors += 1
            if errors <= 3:
                print(f"  Error at 0x{addr:08X}: expected 0x{expected:08X}, got 0x{actual}")
    
    ser.close()
    
    if errors == 0:
        print(f"  Verification PASSED ({sample_count} samples)")
        return True
    else:
        print(f"  Verification FAILED: {errors}/{sample_count} errors")
        return False


def main():
    parser = argparse.ArgumentParser(description='Upload NES ROM to SDRAM')
    parser.add_argument('rom', help='NES ROM file (.nes)')
    parser.add_argument('--port', default='/dev/ttyUSB0', help='Serial port')
    parser.add_argument('--baudrate', type=int, default=115200, help='Baud rate')
    parser.add_argument('--method', choices=['auto', 'client', 'uart'], default='auto',
                       help='Upload method (auto tries client first)')
    parser.add_argument('--chr', action='store_true', help='Also upload CHR-ROM')
    parser.add_argument('--verify', action='store_true', help='Verify after upload')
    args = parser.parse_args()
    
    # Read ROM file
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
    
    print(f"\n{'='*60}")
    print(f"NES ROM: {args.rom}")
    print(f"{'='*60}")
    print(f"  PRG-ROM: {info['prg_size'] // 1024}KB ({info['prg_banks']} banks)")
    print(f"  CHR-ROM: {info['chr_size'] // 1024}KB ({info['chr_banks']} banks)")
    print(f"  Mapper:  {info['mapper']}")
    print(f"  Mirror:  {info['mirroring']}")
    print()
    
    if info['mapper'] != 0:
        print(f"WARNING: Mapper {info['mapper']} - only NROM (0) fully supported")
    
    # Extract ROM data
    header_size = 16
    trainer_size = 512 if info['has_trainer'] else 0
    prg_offset = header_size + trainer_size
    chr_offset = prg_offset + info['prg_size']
    
    prg_data = rom_data[prg_offset:prg_offset + info['prg_size']]
    chr_data = rom_data[chr_offset:chr_offset + info['chr_size']] if info['chr_size'] > 0 else b''
    
    # Choose upload method
    method = args.method
    if method == 'auto':
        try:
            from litex import RemoteClient
            method = 'client'
            print("Using LiteX RemoteClient (fast)")
        except ImportError:
            method = 'uart'
            print("LiteX RemoteClient not available, using UART (slow)")
    
    # Upload PRG-ROM
    if method == 'client':
        success = upload_with_litex_client(PRG_ROM_BASE, prg_data, "PRG-ROM")
    else:
        success = upload_with_uart_fast(PRG_ROM_BASE, prg_data, "PRG-ROM", 
                                        args.port, args.baudrate)
    
    if not success:
        return 1
    
    # Upload CHR-ROM if requested
    if args.chr and chr_data:
        if method == 'client':
            success = upload_with_litex_client(CHR_ROM_BASE, chr_data, "CHR-ROM")
        else:
            success = upload_with_uart_fast(CHR_ROM_BASE, chr_data, "CHR-ROM",
                                           args.port, args.baudrate)
        if not success:
            return 1
    
    # Verify if requested
    if args.verify:
        if not verify_data(PRG_ROM_BASE, prg_data, "PRG-ROM", args.port, args.baudrate):
            return 1
        if args.chr and chr_data:
            if not verify_data(CHR_ROM_BASE, chr_data, "CHR-ROM", args.port, args.baudrate):
                return 1
    
    print(f"\n{'='*60}")
    print("ROM upload complete!")
    print(f"  PRG-ROM at 0x{PRG_ROM_BASE:08X} ({len(prg_data)} bytes)")
    if args.chr and chr_data:
        print(f"  CHR-ROM at 0x{CHR_ROM_BASE:08X} ({len(chr_data)} bytes)")
    print(f"{'='*60}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
