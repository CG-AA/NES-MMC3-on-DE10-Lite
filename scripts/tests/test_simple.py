#!/usr/bin/env python3
"""
Ultra-simple SDRAM test - just verify reads/writes work.
Uses simple delays, no fancy flow control.
"""

import serial
import time

ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=2)
time.sleep(0.5)

print("="*70)
print("SIMPLE SDRAM TEST WITH SAFE TIMINGS")
print("="*70)

# Clear
ser.reset_input_buffer()
ser.write(b'\r\n')
time.sleep(0.2)
ser.read(ser.in_waiting)

print("\nTest 1: Write and read at 0x40000000")
ser.write(b'mem_write 0x40000000 0xDEADBEEF\r\n')
time.sleep(0.05)
ser.read(ser.in_waiting)

ser.write(b'mem_read 0x40000000 4\r\n')
time.sleep(0.05)
result = ser.read(2000).decode('utf-8', errors='replace')
print(result)

print("\nTest 2: Write and read at 0x40001000")
ser.write(b'mem_write 0x40001000 0xCAFEBABE\r\n')
time.sleep(0.05)
ser.read(ser.in_waiting)

ser.write(b'mem_read 0x40001000 4\r\n')
time.sleep(0.05)
result = ser.read(2000).decode('utf-8', errors='replace')
print(result)

print("\nTest 3: Write and read at 0x40002000")
ser.write(b'mem_write 0x40002000 0x12345678\r\n')
time.sleep(0.05)
ser.read(ser.in_waiting)

ser.write(b'mem_read 0x40002000 4\r\n')
time.sleep(0.05)
result = ser.read(2000).decode('utf-8', errors='replace')
print(result)

ser.close()
print("\n" + "="*70)
print("Check if the values match what was written.")
print("If YES: Safe SDRAM timings are working!")
print("If NO: Further investigation needed.")
print("="*70)
