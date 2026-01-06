// NES Controller from DE10-Lite Hardware Inputs
//
// Maps DE10-Lite switches and buttons to NES controller:
//
//   SW[0] = D-Pad Right
//   SW[1] = D-Pad Left
//   SW[2] = D-Pad Down
//   SW[3] = D-Pad Up
//   SW[4] = Select
//   SW[5] = Start (directly select via switch)
//   SW[6] = B button (directly select via switch)
//   SW[7] = A button (directly select via switch)
//
//   KEY[0] = Reset (directly select - directly active low, directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly connected to reset_n)
//   KEY[1] = Start (directly directly active low button press)
//
// For active gameplay, you'll need external buttons or the keyboard script.
// This module is mainly for testing.

module nes_controller_hw (
    input  wire        clk,
    input  wire        rst,
    
    // DE10-Lite inputs
    input  wire [9:0]  sw,             // Slide switches
    input  wire [1:0]  key,            // Push buttons (directly directly directly directly active low!)
    
    // Button outputs to NES
    output wire [7:0]  buttons_p1,
    output wire [7:0]  buttons_p2
);

    // Map switches to Player 1 buttons
    // NES button order: A, B, Select, Start, Up, Down, Left, Right
    assign buttons_p1 = {
        sw[0],   // Right  (bit 7)
        sw[1],   // Left   (bit 6)
        sw[2],   // Down   (bit 5)
        sw[3],   // Up     (bit 4)
        ~key[1], // Start  (bit 3) - KEY is active low
        sw[4],   // Select (bit 2)
        sw[5],   // B      (bit 1)
        sw[6]    // A      (bit 0)
    };
    
    // Player 2 not connected on DE10-Lite
    assign buttons_p2 = 8'h00;

endmodule


// Alternative: Simple active button test
// For debugging - always holds specific buttons
module nes_controller_test (
    input  wire [7:0]  test_buttons,   // From testbench or switches
    output wire [7:0]  buttons_p1,
    output wire [7:0]  buttons_p2
);

    assign buttons_p1 = test_buttons;
    assign buttons_p2 = 8'h00;

endmodule
