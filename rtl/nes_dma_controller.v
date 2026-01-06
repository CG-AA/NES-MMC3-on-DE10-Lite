// NES OAM DMA Controller
// Implements bus-mastering DMA for sprite memory uploads
// Triggered by write to $4014, transfers 256 bytes to PPU $2004
//
// Supports variable-latency memory sources (BRAM or SDRAM via bridge)
// Uses mem_ack signal to wait for memory response

module nes_dma_controller (
    input  wire        clk,
    input  wire        rst,
    input  wire        cpu_clk_en,
    
    // Trigger from address decoder
    input  wire        oam_dma_trigger,  // Write to $4014
    input  wire [7:0]  oam_dma_page,     // Value written to $4014
    
    // Bus control signals
    output reg         dma_active,
    output reg  [15:0] dma_addr,         // Address to drive on bus
    output reg  [7:0]  dma_data,         // Data for OAM write
    output reg         dma_read,         // 1=reading from source
    output reg         dma_write,        // 1=writing to $2004
    output wire [7:0]  dma_byte_count,   // Current byte being transferred (for debug)
    
    // Read data from bus
    input  wire [7:0]  bus_data_in,
    
    // Memory acknowledge (directly from BRAM, or via bridge for SDRAM)
    // For BRAM sources: tie to 1 (always ready)
    // For SDRAM sources: bridge asserts when data is valid
    input  wire        mem_ack,
    
    // CPU halt signal (use with T65 Enable)
    output wire        cpu_halt
);

    // State machine
    localparam IDLE      = 3'd0;
    localparam ALIGN     = 3'd1;  // Wait for odd cycle
    localparam READ      = 3'd2;
    localparam READ_WAIT = 3'd3;  // Wait for memory response
    localparam WRITE     = 3'd4;
    localparam DONE      = 3'd5;
    
    reg [2:0]  state;
    reg [7:0]  byte_count;
    reg [7:0]  source_page;
    reg        cycle_odd;
    reg [7:0]  read_latch;
    
    assign cpu_halt = (state != IDLE);
    assign dma_byte_count = byte_count;
    
    always @(posedge clk) begin
        if (rst) begin
            state <= IDLE;
            dma_active <= 1'b0;
            dma_read <= 1'b0;
            dma_write <= 1'b0;
            cycle_odd <= 1'b0;
            byte_count <= 8'd0;
            source_page <= 8'd0;
            dma_addr <= 16'd0;
            dma_data <= 8'd0;
            read_latch <= 8'd0;
        end else if (cpu_clk_en) begin
            // Track odd/even CPU cycles
            cycle_odd <= ~cycle_odd;
            
            case (state)
                IDLE: begin
                    dma_active <= 1'b0;
                    dma_read <= 1'b0;
                    dma_write <= 1'b0;
                    if (oam_dma_trigger) begin
                        source_page <= oam_dma_page;
                        byte_count <= 8'd0;
                        state <= ALIGN;
                        dma_active <= 1'b1;
                    end
                end
                
                ALIGN: begin
                    // Wait for odd cycle alignment (per NES hardware)
                    if (cycle_odd) begin
                        state <= READ;
                    end
                end
                
                READ: begin
                    // Drive source address and assert read
                    dma_addr <= {source_page, byte_count};
                    dma_read <= 1'b1;
                    dma_write <= 1'b0;
                    state <= READ_WAIT;
                end
                
                READ_WAIT: begin
                    // Wait for memory acknowledge before latching data
                    // For BRAM: mem_ack=1, transitions immediately
                    // For SDRAM: mem_ack asserted after bridge completes fetch
                    if (mem_ack) begin
                        read_latch <= bus_data_in;
                        dma_read <= 1'b0;
                        // Pre-set write signals HERE so they're valid on next cpu_clk_en
                        // when dma_ppu_wr is sampled
                        dma_addr <= 16'h2004;
                        dma_data <= bus_data_in;  // Use bus_data_in directly, not read_latch
                        dma_write <= 1'b1;
                        state <= WRITE;
                    end
                    // else: stay in READ_WAIT, keep dma_read asserted
                end
                
                WRITE: begin
                    // Write signals already set in READ_WAIT
                    // Now transition to next byte or done
                    dma_write <= 1'b0;  // Clear write after one cycle
                    
                    if (byte_count == 8'd255) begin
                        state <= DONE;
                    end else begin
                        byte_count <= byte_count + 8'd1;
                        state <= READ;
                    end
                end
                
                DONE: begin
                    dma_active <= 1'b0;
                    dma_read <= 1'b0;
                    dma_write <= 1'b0;
                    state <= IDLE;
                end
                
                default: begin
                    state <= IDLE;
                end
            endcase
        end
    end

endmodule
