#!/usr/bin/env python3
"""
Keyboard to NES Controller - Direct UART Mode

Captures laptop keyboard input and sends button states to the NES via UART.
The FPGA has a standalone UART receiver that directly drives controller input.

Button mapping:
    W / Up Arrow     = D-Pad Up
    S / Down Arrow   = D-Pad Down  
    A / Left Arrow   = D-Pad Left
    D / Right Arrow  = D-Pad Right
    J / Z            = B Button
    K / X            = A Button
    Enter            = Start
    Right Shift      = Select
    Space            = A Button (alternative)

Usage:
    python keyboard_controller.py --port /dev/ttyUSB0
    python keyboard_controller.py --debug  # No hardware

Hardware Setup:
    USB-UART adapter (CP2102/CH340/FTDI) to DE10-Lite GPIO header JP1:
      - Adapter TX  → JP1 Pin 1 (GPIO[0] = FPGA RX input)
      - Adapter GND → JP1 Pin 29 or 30
    Settings: 115200 baud, 8N1
"""

import argparse
import sys
import time
import threading

try:
    from pynput import keyboard
except ImportError:
    print("Error: pynput not installed. Run: pip install pynput")
    sys.exit(1)

try:
    import serial
except ImportError:
    print("Error: pyserial not installed. Run: pip install pyserial")
    sys.exit(1)


# NES Controller bit positions (directly matches RTL button order)
# Bits: [7:0] = Right, Left, Down, Up, Start, Select, B, A
NES_A      = 0b00000001  # bit 0
NES_B      = 0b00000010  # bit 1
NES_SELECT = 0b00000100  # bit 2
NES_START  = 0b00001000  # bit 3
NES_UP     = 0b00010000  # bit 4
NES_DOWN   = 0b00100000  # bit 5
NES_LEFT   = 0b01000000  # bit 6
NES_RIGHT  = 0b10000000  # bit 7


# Keyboard to NES button mapping
KEY_MAP = {
    # D-Pad (WASD)
    'w': NES_UP,
    's': NES_DOWN,
    'a': NES_LEFT,
    'd': NES_RIGHT,
    # D-Pad (Arrow keys)
    keyboard.Key.up: NES_UP,
    keyboard.Key.down: NES_DOWN,
    keyboard.Key.left: NES_LEFT,
    keyboard.Key.right: NES_RIGHT,
    # Action buttons
    'j': NES_B,
    'k': NES_A,
    'z': NES_B,
    'x': NES_A,
    # Start/Select
    keyboard.Key.enter: NES_START,
    keyboard.Key.shift_r: NES_SELECT,
    keyboard.Key.space: NES_A,  # Alternative A
}


class NESController:
    """Handles keyboard input and sends to NES via UART."""
    
    def __init__(self, port='/dev/ttyUSB0', baudrate=115200, debug=False, 
                 continuous=False, rate=60):
        self.port = port
        self.baudrate = baudrate
        self.debug = debug
        self.continuous = continuous
        self.rate = rate
        self.button_state = 0
        self.ser = None
        self.running = False
        self.last_state = -1
        self.send_thread = None
        self.lock = threading.Lock()
        
    def connect(self):
        """Connect to UART."""
        if self.debug:
            print("Debug mode - no UART connection")
            return True
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=0.1)
            print(f"Connected to {self.port} at {self.baudrate} baud")
            return True
        except serial.SerialException as e:
            print(f"Error connecting to {self.port}: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from UART."""
        self.running = False
        if self.send_thread:
            self.send_thread.join(timeout=1.0)
        if self.ser:
            self.ser.close()
            self.ser = None
    
    def _continuous_sender(self):
        """Background thread for continuous button state transmission."""
        interval = 1.0 / self.rate
        while self.running:
            with self.lock:
                state = self.button_state
            if self.ser:
                try:
                    self.ser.write(bytes([state]))
                except serial.SerialException:
                    pass
            time.sleep(interval)
    
    def send_button_state(self):
        """Send current button state to NES via UART."""
        with self.lock:
            state = self.button_state
            if state == self.last_state:
                return
            self.last_state = state
        
        # Display current state
        self._display_state(state)
        
        # Send via UART (if not in continuous mode, which handles sending)
        if not self.continuous and self.ser:
            try:
                self.ser.write(bytes([state]))
            except serial.SerialException as e:
                print(f"\nUART error: {e}")
    
    def _display_state(self, state):
        """Display gamepad-style button visualization."""
        # Build button list
        buttons = []
        if state & NES_UP:     buttons.append('↑')
        if state & NES_DOWN:   buttons.append('↓')
        if state & NES_LEFT:   buttons.append('←')
        if state & NES_RIGHT:  buttons.append('→')
        if state & NES_SELECT: buttons.append('SEL')
        if state & NES_START:  buttons.append('START')
        if state & NES_B:      buttons.append('B')
        if state & NES_A:      buttons.append('A')
        
        btn_str = ' '.join(buttons) if buttons else '(none)'
        print(f"\r[0x{state:02X}] {btn_str:40}", end='', flush=True)
    
    def on_press(self, key):
        """Handle key press."""
        btn = self._get_button(key)
        if btn:
            with self.lock:
                self.button_state |= btn
            self.send_button_state()
    
    def on_release(self, key):
        """Handle key release."""
        if key == keyboard.Key.esc:
            print("\n\nExiting...")
            self.running = False
            return False
        
        btn = self._get_button(key)
        if btn:
            with self.lock:
                self.button_state &= ~btn
            self.send_button_state()
    
    def _get_button(self, key):
        """Map key to NES button."""
        if key in KEY_MAP:
            return KEY_MAP[key]
        try:
            char = key.char.lower()
            if char in KEY_MAP:
                return KEY_MAP[char]
        except AttributeError:
            pass
        return None
    
    def run(self):
        """Main loop - capture keyboard input."""
        print("\n" + "=" * 60)
        print("       NES Keyboard Controller")
        print("=" * 60)
        print()
        print("  D-Pad:   WASD or Arrow keys")
        print("  B:       J or Z")
        print("  A:       K or X or Space")
        print("  Start:   Enter")
        print("  Select:  Right Shift")
        print("  Quit:    ESC")
        print()
        print("-" * 60)
        
        if self.debug:
            print("Mode: DEBUG (no UART)")
        elif self.ser:
            mode = "CONTINUOUS" if self.continuous else "ON-CHANGE"
            print(f"Mode: {mode} → {self.port}")
            if self.continuous:
                print(f"Rate: {self.rate} Hz")
        else:
            print("Mode: NO CONNECTION")
        print("-" * 60)
        print()
        
        self.running = True
        
        # Start continuous sender if enabled
        if self.continuous and self.ser:
            self.send_thread = threading.Thread(target=self._continuous_sender)
            self.send_thread.daemon = True
            self.send_thread.start()
        
        # Start keyboard listener
        with keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release
        ) as listener:
            listener.join()
        
        print("\nController stopped")


def main():
    parser = argparse.ArgumentParser(
        description='NES Keyboard Controller - Send keyboard input to NES via UART',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Connect to USB-UART adapter
    python keyboard_controller.py --port /dev/ttyUSB0
    
    # Continuous mode (send state at 60Hz regardless of changes)
    python keyboard_controller.py --port /dev/ttyUSB0 --continuous
    
    # Debug mode (no hardware needed)
    python keyboard_controller.py --debug

Hardware Wiring (JP1 GPIO Header):
    ┌──────────────────────────────────────┐
    │  USB-UART Adapter    DE10-Lite JP1   │
    │  ─────────────────   ──────────────  │
    │  TX  ───────────────► Pin 1 (GPIO0)  │
    │  GND ───────────────► Pin 29/30      │
    └──────────────────────────────────────┘
"""
    )
    parser.add_argument('--port', default='/dev/ttyUSB0',
                        help='UART port (default: /dev/ttyUSB0)')
    parser.add_argument('--baud', type=int, default=115200,
                        help='Baud rate (default: 115200)')
    parser.add_argument('--debug', action='store_true',
                        help='Debug mode - show button state without UART')
    parser.add_argument('--continuous', '-c', action='store_true',
                        help='Continuous mode - send state at fixed rate')
    parser.add_argument('--rate', type=int, default=60,
                        help='Send rate in Hz for continuous mode (default: 60)')
    
    args = parser.parse_args()
    
    controller = NESController(
        port=args.port,
        baudrate=args.baud,
        debug=args.debug,
        continuous=args.continuous,
        rate=args.rate
    )
    
    if not controller.connect():
        if not args.debug:
            print("Failed to connect. Running in debug mode.")
            controller.debug = True
    
    try:
        controller.run()
    except KeyboardInterrupt:
        print("\n\nInterrupted")
    finally:
        controller.disconnect()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
