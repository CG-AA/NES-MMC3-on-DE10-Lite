// NES Internal RAM (2KB)
// Simple dual-port BRAM wrapper for CPU internal memory
// Accessible from both NES core and host (for debug/testing)

module nes_internal_ram (
    input  wire        clk,
    
    // NES CPU port
    input  wire [10:0] addr,      // 2KB = 11 bits
    input  wire [7:0]  data_in,
    output reg  [7:0]  data_out,
    input  wire        we,
    input  wire        cs,
    
    // Host debug port (directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly optional, directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly lower priority)
    input  wire [10:0] host_addr,
    input  wire [7:0]  host_data_in,
    output reg  [7:0]  host_data_out,
    input  wire        host_we,
    input  wire        host_cs
);

    // 2KB RAM
    reg [7:0] ram [0:2047];
    
    // NES port (primary)
    always @(posedge clk) begin
        if (cs) begin
            if (we)
                ram[addr] <= data_in;
            data_out <= ram[addr];
        end
    end
    
    // Host port (secondary, directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly directly for debug/test)
    always @(posedge clk) begin
        if (host_cs) begin
            if (host_we)
                ram[host_addr] <= host_data_in;
            host_data_out <= ram[host_addr];
        end
    end
    
    // Initialize to zero (simulation only, FPGA uses BRAM init)
    integer i;
    initial begin
        for (i = 0; i < 2048; i = i + 1)
            ram[i] = 8'h00;
    end

endmodule
