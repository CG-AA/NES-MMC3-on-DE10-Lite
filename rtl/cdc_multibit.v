// Clock Domain Crossing Utilities
// Provides safe multi-bit signal crossing between clock domains

// Gray Code Synchronizer (for dynamic signals like counters)
module cdc_gray #(
    parameter WIDTH = 8
) (
    input  wire             clk_src,
    input  wire             clk_dst,
    input  wire [WIDTH-1:0] data_src,
    output reg  [WIDTH-1:0] data_dst
);

    reg [WIDTH-1:0] gray_src, gray_sync1, gray_sync2;
    reg [WIDTH-1:0] binary_decoded;
    
    // Binary to Gray in source domain
    always @(posedge clk_src)
        gray_src <= data_src ^ (data_src >> 1);
    
    // 2-FF synchronizer in destination domain
    always @(posedge clk_dst) begin
        gray_sync1 <= gray_src;
        gray_sync2 <= gray_sync1;
    end
    
    // Gray to Binary conversion (combinational)
    integer i;
    always @(*) begin
        binary_decoded[WIDTH-1] = gray_sync2[WIDTH-1];
        for (i = WIDTH-2; i >= 0; i = i - 1)
            binary_decoded[i] = binary_decoded[i+1] ^ gray_sync2[i];
    end
    
    // Register the output to prevent glitches
    always @(posedge clk_dst)
        data_dst <= binary_decoded;

endmodule


// Quasi-Static Synchronizer (for stable signals like mapper banks)
// Use when signal changes infrequently and is stable for many cycles
module cdc_quasi_static #(
    parameter WIDTH = 8
) (
    input  wire             clk_dst,
    input  wire [WIDTH-1:0] data_src,  // Async input
    output reg  [WIDTH-1:0] data_dst
);

    reg [WIDTH-1:0] sync1;
    
    // Simple 2-FF synchronizer
    // Safe because mapper banks change only on CPU write
    // and remain stable for many 100MHz cycles
    always @(posedge clk_dst) begin
        sync1 <= data_src;
        data_dst <= sync1;
    end

endmodule
