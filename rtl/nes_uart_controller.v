// UART Receiver for Controller Input - 16x Oversampling
// 
// Receives 1-byte controller state directly over UART.
// Uses 16x oversampling for robust reception.
//
// Protocol:
//   - 115200 baud, 8N1
//   - Each byte = button state (A,B,Sel,Start,U,D,L,R)
//   - Send continuously at ~60Hz for responsive input

module nes_uart_controller #(
    parameter CLK_FREQ  = 50_000_000,
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
    output reg        rx_valid,
    output wire       uart_active
);

    // 16x oversampling clock
    // For 115200 baud: sample at 115200 * 16 = 1,843,200 Hz
    // Divider: 50_000_000 / 1_843_200 = 27.13 -> use 27
    localparam OVERSAMPLE = 16;
    localparam SAMPLE_DIV = CLK_FREQ / (BAUD_RATE * OVERSAMPLE);
    
    // Sample clock generator
    reg [$clog2(SAMPLE_DIV)-1:0] sample_cnt;
    reg sample_tick;
    
    always @(posedge clk) begin
        if (rst) begin
            sample_cnt <= 0;
            sample_tick <= 0;
        end else begin
            if (sample_cnt >= SAMPLE_DIV - 1) begin
                sample_cnt <= 0;
                sample_tick <= 1;
            end else begin
                sample_cnt <= sample_cnt + 1;
                sample_tick <= 0;
            end
        end
    end
    
    // Synchronize and filter RX input (3-stage for metastability + majority vote)
    reg rx_sync1, rx_sync2, rx_sync3;
    reg [2:0] rx_filter;
    reg rx_filtered;
    
    always @(posedge clk) begin
        if (rst) begin
            rx_sync1 <= 1;
            rx_sync2 <= 1;
            rx_sync3 <= 1;
            rx_filter <= 3'b111;
            rx_filtered <= 1;
        end else begin
            // Metastability synchronizer
            rx_sync1 <= uart_rx;
            rx_sync2 <= rx_sync1;
            rx_sync3 <= rx_sync2;
            
            // Shift register filter (majority vote on sample_tick)
            if (sample_tick) begin
                rx_filter <= {rx_filter[1:0], rx_sync3};
                // Majority vote: 2 out of 3
                case (rx_filter)
                    3'b000, 3'b001, 3'b010, 3'b100: rx_filtered <= 0;
                    default: rx_filtered <= 1;
                endcase
            end
        end
    end
    
    // UART receiver state machine
    localparam IDLE = 0, START = 1, DATA = 2, STOP = 3;
    reg [1:0] state;
    reg [3:0] tick_cnt;     // Count 16 ticks per bit
    reg [2:0] bit_cnt;      // Count 8 data bits
    reg [7:0] shift_reg;
    reg rx_done;
    
    always @(posedge clk) begin
        if (rst) begin
            state <= IDLE;
            tick_cnt <= 0;
            bit_cnt <= 0;
            shift_reg <= 0;
            rx_done <= 0;
            rx_valid <= 0;
        end else begin
            rx_done <= 0;
            rx_valid <= 0;
            
            if (sample_tick) begin
                case (state)
                    IDLE: begin
                        tick_cnt <= 0;
                        bit_cnt <= 0;
                        // Detect falling edge (start bit)
                        if (!rx_filtered) begin
                            state <= START;
                            tick_cnt <= 0;
                        end
                    end
                    
                    START: begin
                        tick_cnt <= tick_cnt + 1;
                        // Sample at middle of start bit (tick 7-8)
                        if (tick_cnt == 7) begin
                            if (!rx_filtered) begin
                                // Valid start bit - move to data
                                state <= DATA;
                                tick_cnt <= 0;
                                bit_cnt <= 0;
                            end else begin
                                // False start (noise)
                                state <= IDLE;
                            end
                        end
                    end
                    
                    DATA: begin
                        tick_cnt <= tick_cnt + 1;
                        // Sample at middle of each bit (after 16 ticks = 1 bit time)
                        if (tick_cnt == 15) begin
                            tick_cnt <= 0;
                            // Shift in new bit (LSB first, so new bit goes to MSB, shift right)
                            shift_reg <= {rx_filtered, shift_reg[7:1]};
                            bit_cnt <= bit_cnt + 1;
                            if (bit_cnt == 7) begin
                                // All 8 bits received
                                state <= STOP;
                            end
                        end
                    end
                    
                    STOP: begin
                        tick_cnt <= tick_cnt + 1;
                        // Sample middle of stop bit
                        if (tick_cnt == 15) begin
                            if (rx_filtered) begin
                                // Valid stop bit - byte complete
                                rx_done <= 1;
                                rx_valid <= 1;
                            end
                            // Return to idle regardless
                            state <= IDLE;
                            tick_cnt <= 0;
                        end
                    end
                endcase
            end
        end
    end
    
    // Protocol handler
    reg waiting_p2;
    
    // UART activity timeout - stays high for ~100ms after last byte received
    reg [22:0] uart_timeout_cnt;
    assign uart_active = (uart_timeout_cnt != 0);
    
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
                waiting_p2 <= 0;
            end else if (shift_reg == 8'hC2) begin
                waiting_p2 <= 1;
            end else begin
                if (waiting_p2)
                    buttons_p2 <= shift_reg;
                else
                    buttons_p1 <= shift_reg;
            end
        end else if (uart_timeout_cnt != 0) begin
            uart_timeout_cnt <= uart_timeout_cnt - 1;
            if (uart_timeout_cnt == 1) begin
                buttons_p1 <= 8'h00;
                buttons_p2 <= 8'h00;
            end
        end
    end

endmodule
