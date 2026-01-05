#!/usr/bin/env python3
"""Test SFL protocol upload to SDRAM"""

import serial
import time
import struct

# SFL Protocol
sfl_magic_req = b'sL5DdSMmkekro\n'
sfl_magic_ack = b'z6IHG7cYDID6o\n'
sfl_cmd_abort = b'\x00'
sfl_cmd_load = b'\x01'
sfl_cmd_jump = b'\x02'
sfl_ack_success = b'K'

crc16_table = [
    0x0000, 0x1021, 0x2042, 0x3063, 0x4084, 0x50A5, 0x60C6, 0x70E7,
    0x8108, 0x9129, 0xA14A, 0xB16B, 0xC18C, 0xD1AD, 0xE1CE, 0xF1EF,
    0x1231, 0x0210, 0x3273, 0x2252, 0x52B5, 0x4294, 0x72F7, 0x62D6,
    0x9339, 0x8318, 0xB37B, 0xA35A, 0xD3BD, 0xC39C, 0xF3FF, 0xE3DE,
    0x2462, 0x3443, 0x0420, 0x1401, 0x64E6, 0x74C7, 0x44A4, 0x5485,
    0xA56A, 0xB54B, 0x8528, 0x9509, 0xE5EE, 0xF5CF, 0xC5AC, 0xD58D,
    0x3653, 0x2672, 0x1611, 0x0630, 0x76D7, 0x66F6, 0x5695, 0x46B4,
    0xB75B, 0xA77A, 0x9719, 0x8738, 0xF7DF, 0xE7FE, 0xD79D, 0xC7BC,
    0x48C4, 0x58E5, 0x6886, 0x78A7, 0x0840, 0x1861, 0x2802, 0x3823,
    0xC9CC, 0xD9ED, 0xE98E, 0xF9AF, 0x8948, 0x9969, 0xA90A, 0xB92B,
    0x5AF5, 0x4AD4, 0x7AB7, 0x6A96, 0x1A71, 0x0A50, 0x3A33, 0x2A12,
    0xDBFD, 0xCBDC, 0xFBBF, 0xEB9E, 0x9B79, 0x8B58, 0xBB3B, 0xAB1A,
    0x6CA6, 0x7C87, 0x4CE4, 0x5CC5, 0x2C22, 0x3C03, 0x0C60, 0x1C41,
    0xEDAE, 0xFD8F, 0xCDEC, 0xDDCD, 0xAD2A, 0xBD0B, 0x8D68, 0x9D49,
    0x7E97, 0x6EB6, 0x5ED5, 0x4EF4, 0x3E13, 0x2E32, 0x1E51, 0x0E70,
    0xFF9F, 0xEFBE, 0xDFDD, 0xCFFC, 0xBF1B, 0xAF3A, 0x9F59, 0x8F78,
    0x9188, 0x81A9, 0xB1CA, 0xA1EB, 0xD10C, 0xC12D, 0xF14E, 0xE16F,
    0x1080, 0x00A1, 0x30C2, 0x20E3, 0x5004, 0x4025, 0x7046, 0x6067,
    0x83B9, 0x9398, 0xA3FB, 0xB3DA, 0xC33D, 0xD31C, 0xE37F, 0xF35E,
    0x02B1, 0x1290, 0x22F3, 0x32D2, 0x4235, 0x5214, 0x6277, 0x7256,
    0xB5EA, 0xA5CB, 0x95A8, 0x8589, 0xF56E, 0xE54F, 0xD52C, 0xC50D,
    0x34E2, 0x24C3, 0x14A0, 0x0481, 0x7466, 0x6447, 0x5424, 0x4405,
    0xA7DB, 0xB7FA, 0x8799, 0x97B8, 0xE75F, 0xF77E, 0xC71D, 0xD73C,
    0x26D3, 0x36F2, 0x0691, 0x16B0, 0x6657, 0x7676, 0x4615, 0x5634,
    0xD94C, 0xC96D, 0xF90E, 0xE92F, 0x99C8, 0x89E9, 0xB98A, 0xA9AB,
    0x5844, 0x4865, 0x7806, 0x6827, 0x18C0, 0x08E1, 0x3882, 0x28A3,
    0xCB7D, 0xDB5C, 0xEB3F, 0xFB1E, 0x8BF9, 0x9BD8, 0xABBB, 0xBB9A,
    0x4A75, 0x5A54, 0x6A37, 0x7A16, 0x0AF1, 0x1AD0, 0x2AB3, 0x3A92,
    0xFD2E, 0xED0F, 0xDD6C, 0xCD4D, 0xBDAA, 0xAD8B, 0x9DE8, 0x8DC9,
    0x7C26, 0x6C07, 0x5C64, 0x4C45, 0x3CA2, 0x2C83, 0x1CE0, 0x0CC1,
    0xEF1F, 0xFF3E, 0xCF5D, 0xDF7C, 0xAF9B, 0xBFBA, 0x8FD9, 0x9FF8,
    0x6E17, 0x7E36, 0x4E55, 0x5E74, 0x2E93, 0x3EB2, 0x0ED1, 0x1EF0
]

def crc16(data):
    crc = 0
    for d in data:
        crc = crc16_table[((crc >> 8) ^ d) & 0xff] ^ (crc << 8)
    return crc & 0xffff

def make_sfl_frame(cmd, payload):
    data = cmd + payload
    crc = crc16(data)
    return bytes([len(payload)]) + crc.to_bytes(2, 'big') + data

def sfl_upload(ser, data, address):
    # Trigger serialboot
    ser.reset_input_buffer()
    ser.write(b'serialboot\r\n')
    
    # Wait for magic request
    buf = b''
    for _ in range(100):
        if ser.in_waiting:
            buf += ser.read(ser.in_waiting)
        if sfl_magic_req in buf:
            break
        time.sleep(0.02)
    else:
        print(f'No SFL magic received')
        return False
    
    print('SFL handshake OK')
    ser.write(sfl_magic_ack)
    time.sleep(0.05)
    
    # Upload
    chunk_size = 251
    sent = 0
    errors = 0
    start = time.time()
    
    while sent < len(data):
        chunk = data[sent:sent + chunk_size]
        payload = struct.pack('>I', address + sent) + chunk
        frame = make_sfl_frame(sfl_cmd_load, payload)
        ser.write(frame)
        
        # Wait for ACK
        ack = b''
        for _ in range(50):
            if ser.in_waiting:
                ack = ser.read(1)
                break
            time.sleep(0.002)
        
        if ack != sfl_ack_success:
            errors += 1
        sent += len(chunk)
        
        if sent % 4096 == 0 or sent == len(data):
            elapsed = time.time() - start
            rate = sent / elapsed if elapsed > 0 else 0
            print(f'  {sent}/{len(data)} bytes - {rate:.0f} B/s')
    
    elapsed = time.time() - start
    print(f'Done: {len(data)} bytes in {elapsed:.2f}s ({len(data)/elapsed:.0f} B/s), {errors} errors')
    
    # Exit SFL by jumping back to BIOS at 0x00000000
    print('Jumping back to BIOS...')
    import struct as s
    jump_payload = s.pack('>I', 0x00000000)  # Jump to ROM/BIOS
    jump_frame = make_sfl_frame(sfl_cmd_jump, jump_payload)
    ser.write(jump_frame)
    time.sleep(2.0)  # Wait for reboot
    
    return errors == 0

def main():
    ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=2.0)
    time.sleep(0.3)
    
    # Clear any garbage
    ser.reset_input_buffer()
    ser.write(b'\r\n')
    time.sleep(0.2)
    ser.read(1024)

    # Test data - 4KB
    test_data = bytes([i & 0xFF for i in range(4096)])
    print(f'Test data: {len(test_data)} bytes')
    print(f'First 16 bytes: {test_data[:16].hex()}')

    # Upload
    print('\nUploading to SDRAM at 0x40000000...')
    result = sfl_upload(ser, test_data, 0x40000000)

    # Wait for BIOS to recover from SFL mode
    print('\nWaiting for BIOS...')
    time.sleep(1.0)
    ser.reset_input_buffer()
    
    # Send multiple newlines to wake up BIOS
    for i in range(5):
        ser.write(b'\r\n')
        time.sleep(0.2)
        if ser.in_waiting > 10:
            break
    
    ser.read(1024)  # Clear prompt echoes
    
    # Verify
    print('Verifying SDRAM content...')
    ser.write(b'mem_read 0x40000000 64\r\n')
    time.sleep(0.5)
    resp = ser.read(4096).decode('utf-8', errors='replace')
    print('Memory content:')
    for line in resp.split('\n'):
        if '0x40' in line.lower():
            print(f'  {line.strip()}')

    # Check expected vs actual
    print('\nExpected first 16 bytes: 00 01 02 03 04 05 06 07 08 09 0a 0b 0c 0d 0e 0f')

    ser.close()

if __name__ == '__main__':
    main()
