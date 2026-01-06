// Simple UART Receiver for Controller Input
// 
// Receives 1-byte controller state directly over UART.
// No LiteX/BIOS needed - standalone receiver.
//
// Protocol:
//   - 115200 baud, 8N1
//   - Each byte = button state (A,B,Sel,Start,U,D,L,R)
//   - Send continuously at ~60Hz for responsive input
//
// Connect to separate UART port (e.g., GPIO pins)
// or share with LiteX UART using escape sequence protocol.

module nes_uart_controller #(
    parameter CLK_FREQ = 50_000_000,
    parameter BAUD_RATE = 115200
)(
    input  wire       clk,
    input  wire       rst,
    
    // UART input
    input  wire       uart_rx,
    
    // Button output
    output reg [7:0]  buttons_p1,
    output reg [7:0]  buttons_p2,
    
    // Status
    output wire       rx_valid,
    output wire       uart_active   // High when UART has been recently active
);

    // Baud rate generator
    localparam BAUD_DIV = CLK_FREQ / BAUD_RATE;
    localparam HALF_BAUD = BAUD_DIV / 2;
    
    reg [$clog2(BAUD_DIV)-1:0] baud_cnt;
    reg baud_tick;
    
    always @(posedge clk) begin
        if (rst) begin
            baud_cnt <= 0;
            baud_tick <= 0;
        end else begin
            if (baud_cnt == BAUD_DIV - 1) begin
                baud_cnt <= 0;
                baud_tick <= 1;
            end else begin
                baud_cnt <= baud_cnt + 1;
                baud_tick <= 0;
            end
        end
    end
    
    // UART receiver state machine
    localparam IDLE = 0, START = 1, DATA = 2, STOP = 3;
    reg [1:0] state;
    reg [2:0] bit_cnt;
    reg [7:0] shift_reg;
    reg [$clog2(BAUD_DIV)-1:0] sample_cnt;
    reg rx_sync1, rx_sync2;
    reg rx_done;
    
    // Synchronize RX input
    always @(posedge clk) begin
        rx_sync1 <= uart_rx;
        rx_sync2 <= rx_sync1;
    end
    
    always @(posedge clk) begin
        if (rst) begin
            state <= IDLE;
            bit_cnt <= 0;
            shift_reg <= 0;
            sample_cnt <= 0;
            rx_done <= 0;
        end else begin
            rx_done <= 0;
            
            case (state)
                IDLE: begin
                    // Wait for start bit (falling edge)
                    if (!rx_sync2) begin
                        state <= START;
                        sample_cnt <= 0;
                    end
                end
                
                START: begin
                    // Sample at middle of start bit
                    sample_cnt <= sample_cnt + 1;
                    if (sample_cnt == HALF_BAUD) begin
                        if (!rx_sync2) begin
                            // Valid start bit
                            state <= DATA;
                            sample_cnt <= 0;
                            bit_cnt <= 0;
                        end else begin
                            // False start
                            state <= IDLE;
                        end
                    end
                end
                
                DATA: begin
                    // Sample at middle of each data bit (after BAUD_DIV cycles from previous sample)
                    sample_cnt <= sample_cnt + 1;
                    if (sample_cnt == BAUD_DIV - 1) begin
                        sample_cnt <= 0;
                        // Sample happens BAUD_DIV after start bit mid-point = mid-bit
                        shift_reg <= {rx_sync2, shift_reg[7:1]};
                        bit_cnt <= bit_cnt + 1;
                        if (bit_cnt == 7) begin
                            state <= STOP;
                        end
                    end
                end
                
                STOP: begin
                    // Wait for middle of stop bit, then validate
                    sample_cnt <= sample_cnt + 1;
                    if (sample_cnt == HALF_BAUD) begin
                        if (rx_sync2) begin
                            // Valid stop bit - data ready
                            rx_done <= 1;
                        end
                        state <= IDLE;
                        sample_cnt <= 0;
                    end
                end
            endcase
        end
    end
    
    assign rx_valid = rx_done;
    
    // Protocol: 
    //   Byte 0xC1-0xC2 = controller select (P1 or P2)
    //   Following byte = button state
    // Or simple mode: every byte goes to P1
    
    reg waiting_p2;
    
    // UART activity timeout - stays high for ~100ms after last byte received
    // At 50MHz, 100ms = 5,000,000 cycles. Use 23-bit counter.
    reg [22:0] uart_timeout_cnt;
    assign uart_active = (uart_timeout_cnt != 0);  // Output declared in port list
    
    always @(posedge clk) begin
        if (rst) begin
            buttons_p1 <= 8'h00;
            buttons_p2 <= 8'h00;
            waiting_p2 <= 0;
            uart_timeout_cnt <= 0;
        end else if (rx_done) begin
            // Reset timeout on any byte received
            uart_timeout_cnt <= 23'd5_000_000;
            if (shift_reg == 8'hC1) begin
                // Next byte is P1
                waiting_p2 <= 0;
            end else if (shift_reg == 8'hC2) begin
                // Next byte is P2
                waiting_p2 <= 1;
            end else begin
                // Regular button data
                if (waiting_p2)
                    buttons_p2 <= shift_reg;
                else
                    buttons_p1 <= shift_reg;
            end
        end else if (uart_timeout_cnt != 0) begin
            // Decrement timeout counter
            uart_timeout_cnt <= uart_timeout_cnt - 1;
            // Clear buttons when timeout expires (fallback to switches)
            if (uart_timeout_cnt == 1) begin
                buttons_p1 <= 8'h00;
                buttons_p2 <= 8'h00;
            end
        end
    end

endmodule
