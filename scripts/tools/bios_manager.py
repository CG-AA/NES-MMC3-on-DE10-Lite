#!/usr/bin/env python3
"""
BIOS Connection Manager

Provides reliable BIOS connection with automatic detection and recovery.
Use this as a base for all SDRAM test scripts.

Features:
- Auto-detect BIOS presence
- Attempt recovery via FPGA reload
- Provide reliable read/write wrappers
- Handle ANSI escape codes in prompts
"""

import serial
import time
import subprocess
import sys
import os

class BIOSConnection:
    """Manages connection to LiteX BIOS with auto-recovery."""
    
    def __init__(self, port='/dev/ttyUSB0', baudrate=115200, timeout=2):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None
        self.recovery_attempts = 0
        self.max_recovery_attempts = 2
    
    def connect(self):
        """Connect to serial port."""
        if self.ser and self.ser.is_open:
            self.ser.close()
        
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
            time.sleep(0.3)
            return True
        except Exception as e:
            print(f"ERROR: Cannot open {self.port}: {e}")
            return False
    
    def close(self):
        """Close connection."""
        if self.ser and self.ser.is_open:
            self.ser.close()
    
    def check_bios(self):
        """Check if BIOS is responding."""
        if not self.ser or not self.ser.is_open:
            return False
        
        self.ser.reset_input_buffer()
        self.ser.write(b'\r\n')
        time.sleep(0.3)
        response = self.ser.read(self.ser.in_waiting)
        
        # Check for BIOS prompt (handles ANSI codes)
        return b'litex' in response or b'LITEX' in response
    
    def reload_fpga(self):
        """Reload FPGA bitstream to recover BIOS."""
        print("\n" + "="*60)
        print("BIOS not responding - attempting FPGA reload...")
        print("="*60)
        
        # Close serial before reload
        if self.ser and self.ser.is_open:
            self.ser.close()
        
        # Find the load script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        load_cmd = f"python3 {script_dir}/terasic_de10lite_custom.py --load"
        
        try:
            result = subprocess.run(
                load_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0 and "Configuration succeeded" in result.stdout:
                print("✓ FPGA reload successful")
                time.sleep(2)  # Wait for BIOS to initialize
                return True
            else:
                print(f"✗ FPGA reload failed")
                if result.stderr:
                    print(f"  Error: {result.stderr[:200]}")
                return False
                
        except subprocess.TimeoutExpired:
            print("✗ FPGA reload timed out")
            return False
        except Exception as e:
            print(f"✗ FPGA reload error: {e}")
            return False
    
    def ensure_bios(self):
        """Ensure BIOS is responding, with auto-recovery."""
        if not self.connect():
            return False
        
        if self.check_bios():
            print("✓ BIOS responding")
            return True
        
        # Try recovery
        while self.recovery_attempts < self.max_recovery_attempts:
            self.recovery_attempts += 1
            print(f"\nRecovery attempt {self.recovery_attempts}/{self.max_recovery_attempts}...")
            
            if self.reload_fpga():
                if self.connect() and self.check_bios():
                    print("✓ BIOS recovered!")
                    return True
        
        print("✗ Could not recover BIOS")
        return False
    
    def send_command(self, cmd, timeout=0.1):
        """Send command and return response."""
        if not self.ser or not self.ser.is_open:
            return None
        
        self.ser.reset_input_buffer()
        self.ser.write(cmd.encode() + b'\r\n')
        time.sleep(timeout)
        return self.ser.read(self.ser.in_waiting).decode('utf-8', errors='replace')
    
    def mem_write(self, addr, value, delay=0.02):
        """Write 32-bit value to memory."""
        cmd = f'mem_write 0x{addr:08x} 0x{value:08x}'
        self.ser.write(cmd.encode() + b'\r\n')
        time.sleep(delay)
        # Drain response buffer periodically
        if self.ser.in_waiting > 100:
            self.ser.read(self.ser.in_waiting)
    
    def mem_read(self, addr):
        """Read 32-bit value from memory."""
        self.ser.reset_input_buffer()
        self.ser.write(f'mem_read 0x{addr:08x} 4\r\n'.encode())
        time.sleep(0.15)  # Longer delay for reliable response
        resp = self.ser.read(2048).decode('utf-8', errors='replace')
        
        # Parse response - look for hex dump line
        for line in resp.split('\n'):
            # Match lines like "0x40000000  ef be ad de"
            if '0x40' in line:
                parts = line.split()
                # Find the address part and get bytes after it
                for i, p in enumerate(parts):
                    if p.startswith('0x40') and i + 4 < len(parts):
                        try:
                            b = [int(parts[i+1+j], 16) for j in range(4)]
                            return b[0] | (b[1] << 8) | (b[2] << 16) | (b[3] << 24)
                        except:
                            pass
        return None
    
    def verify_connection(self):
        """Quick test to verify SDRAM is working."""
        test_val = 0xDEADBEEF
        test_addr = 0x40000000
        
        # Clear any pending data first
        self.ser.reset_input_buffer()
        time.sleep(0.1)
        
        # Write
        self.mem_write(test_addr, test_val, delay=0.1)
        
        # Read with longer delay
        time.sleep(0.1)
        result = self.mem_read(test_addr)
        
        if result == test_val:
            return True
        else:
            print(f"SDRAM verify failed: wrote 0x{test_val:08X}, read {result}")
            return False


def quick_check():
    """Quick check if BIOS is responding."""
    bios = BIOSConnection()
    
    print("="*60)
    print("BIOS CONNECTION CHECK")
    print("="*60)
    
    if bios.ensure_bios():
        print("\nVerifying SDRAM...")
        if bios.verify_connection():
            print("✓ SDRAM read/write verified")
            print("\n✅ System ready for use!")
            bios.close()
            return True
        else:
            print("✗ SDRAM verification failed")
    
    bios.close()
    return False


def force_reload():
    """Force FPGA reload regardless of current state."""
    bios = BIOSConnection()
    
    print("="*60)
    print("FORCING FPGA RELOAD")
    print("="*60)
    
    if bios.reload_fpga():
        if bios.connect() and bios.check_bios():
            print("\n✓ BIOS responding after reload")
            if bios.verify_connection():
                print("✓ SDRAM verified")
                print("\n✅ System ready!")
                bios.close()
                return True
    
    bios.close()
    return False


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='BIOS Connection Manager')
    parser.add_argument('--check', action='store_true', help='Check BIOS and recover if needed')
    parser.add_argument('--reload', action='store_true', help='Force FPGA reload')
    parser.add_argument('--port', default='/dev/ttyUSB0', help='Serial port')
    args = parser.parse_args()
    
    if args.reload:
        sys.exit(0 if force_reload() else 1)
    else:
        # Default: check with auto-recovery
        sys.exit(0 if quick_check() else 1)
