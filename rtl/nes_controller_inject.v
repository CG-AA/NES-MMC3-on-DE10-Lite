// NES Controller Input via CSR
// 
// This module receives button state from a CSR register (written via UART/Wishbone)
// and provides it to the NES CPU via the standard $4016/$4017 interface.
//
// NES Controller Protocol:
//   - Write to $4016 bit 0 = strobe
//   - When strobe high, shift register continuously loads button state
//   - When strobe goes low, shift register latches
//   - Each read from $4016/$4017 shifts out one bit
//
// Button bit order (active high):
//   Bit 0: A
//   Bit 1: B
//   Bit 2: Select
//   Bit 3: Start
//   Bit 4: Up
//   Bit 5: Down
//   Bit 6: Left
//   Bit 7: Right

module nes_controller_inject (
    input  wire        clk,
    input  wire        rst,
    input  wire        cpu_clk_en,     // CPU clock enable
    
    // Button state input (directly from CSR or GPIO)
    input  wire [7:0]  buttons_p1,     // Player 1 buttons (directly latched)
    input  wire [7:0]  buttons_p2,     // Player 2 buttons
    
    // CPU interface
    input  wire        cs,             // Chip select ($4016/$4017 address decode)
    input  wire [0:0]  addr,           // 0 = $4016 (P1), 1 = $4017 (P2)
    input  wire        we,             // Write enable
    input  wire [7:0]  din,            // Data in (for strobe)
    output reg  [7:0]  dout            // Data out (button bits)
);

    // Shift registers for each controller
    reg [7:0] shift_p1;
    reg [7:0] shift_p2;
    
    // Strobe register
    reg strobe;
    
    // Controller output bits (active low on real hardware, but we use active high internally)
    wire p1_bit = shift_p1[0];
    wire p2_bit = shift_p2[0];
    
    always @(posedge clk) begin
        if (rst) begin
            shift_p1 <= 8'h00;
            shift_p2 <= 8'h00;
            strobe <= 1'b0;
            dout <= 8'h00;
        end else if (cpu_clk_en && cs) begin
            if (we) begin
                // Write to $4016 - control strobe
                strobe <= din[0];
                
                // When strobe is set, continuously reload shift registers
                if (din[0]) begin
                    shift_p1 <= buttons_p1;
                    shift_p2 <= buttons_p2;
                end
            end else begin
                // Read from $4016 or $4017
                if (addr == 1'b0) begin
                    // $4016 - Player 1
                    dout <= {7'b0100000, p1_bit};  // Open bus bits + controller bit
                    
                    // Shift out next bit (only when strobe is low)
                    if (!strobe) begin
                        shift_p1 <= {1'b1, shift_p1[7:1]};  // Shift right, fill with 1s
                    end
                end else begin
                    // $4017 - Player 2
                    dout <= {7'b0100000, p2_bit};
                    
                    if (!strobe) begin
                        shift_p2 <= {1'b1, shift_p2[7:1]};
                    end
                end
            end
        end else begin
            // Strobe high - continuously reload
            if (strobe) begin
                shift_p1 <= buttons_p1;
                shift_p2 <= buttons_p2;
            end
        end
    end

endmodule


// Simple CSR-accessible button register
// This is for direct button state injection from host (UART)
module nes_button_csr (
    input  wire        clk,
    input  wire        rst,
    
    // Wishbone/CSR interface
    input  wire        cyc,
    input  wire        stb,
    input  wire        we,
    input  wire [1:0]  adr,            // 0 = P1, 1 = P2, 2 = status
    input  wire [7:0]  dat_w,
    output reg  [7:0]  dat_r,
    output wire        ack,
    
    // Button outputs to NES
    output reg  [7:0]  buttons_p1,
    output reg  [7:0]  buttons_p2
);

    assign ack = cyc & stb;  // Single-cycle access
    
    always @(posedge clk) begin
        if (rst) begin
            buttons_p1 <= 8'h00;
            buttons_p2 <= 8'h00;
            dat_r <= 8'h00;
        end else if (cyc && stb) begin
            if (we) begin
                case (adr)
                    2'b00: buttons_p1 <= dat_w;
                    2'b01: buttons_p2 <= dat_w;
                    default: ;
                endcase
            end else begin
                case (adr)
                    2'b00: dat_r <= buttons_p1;
                    2'b01: dat_r <= buttons_p2;
                    2'b10: dat_r <= 8'h01;  // Status: controller connected
                    default: dat_r <= 8'h00;
                endcase
            end
        end
    end

endmodule
