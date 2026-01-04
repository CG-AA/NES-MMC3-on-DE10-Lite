// NES Color Palette ROM
// 64 colors from the NES PPU palette
// Output is 12-bit RGB (4 bits per channel)
//
// Based on the "2C02" PPU palette - commonly used reference

module nes_palette (
    input  [5:0] color_index,    // 6-bit palette index (0-63)
    output [3:0] r,
    output [3:0] g,
    output [3:0] b
);

    reg [11:0] rgb;
    
    assign r = rgb[11:8];
    assign g = rgb[7:4];
    assign b = rgb[3:0];
    
    // NES palette - 2C02 reference
    always @(*) begin
        case (color_index)
            // Row 0 (grays and dark colors)
            6'h00: rgb = 12'h666; // Gray
            6'h01: rgb = 12'h00A; // Dark Blue
            6'h02: rgb = 12'h10B; // Blue-Violet
            6'h03: rgb = 12'h40A; // Violet
            6'h04: rgb = 12'h700; // Dark Magenta
            6'h05: rgb = 12'h900; // Dark Red
            6'h06: rgb = 12'h810; // Red-Orange
            6'h07: rgb = 12'h620; // Brown
            6'h08: rgb = 12'h340; // Olive
            6'h09: rgb = 12'h050; // Dark Green
            6'h0A: rgb = 12'h051; // Green
            6'h0B: rgb = 12'h043; // Cyan-Green
            6'h0C: rgb = 12'h036; // Dark Cyan
            6'h0D: rgb = 12'h000; // Black
            6'h0E: rgb = 12'h000; // Black
            6'h0F: rgb = 12'h000; // Black
            
            // Row 1 (medium colors)
            6'h10: rgb = 12'hAAA; // Light Gray
            6'h11: rgb = 12'h06F; // Blue
            6'h12: rgb = 12'h33F; // Light Blue-Violet
            6'h13: rgb = 12'h73F; // Light Violet
            6'h14: rgb = 12'hA3E; // Light Magenta
            6'h15: rgb = 12'hC24; // Red
            6'h16: rgb = 12'hC40; // Orange
            6'h17: rgb = 12'hA50; // Light Brown
            6'h18: rgb = 12'h680; // Yellow-Green
            6'h19: rgb = 12'h092; // Green
            6'h1A: rgb = 12'h0A4; // Cyan-Green
            6'h1B: rgb = 12'h0A8; // Cyan
            6'h1C: rgb = 12'h078; // Light Cyan
            6'h1D: rgb = 12'h000; // Black
            6'h1E: rgb = 12'h000; // Black
            6'h1F: rgb = 12'h000; // Black
            
            // Row 2 (bright colors)
            6'h20: rgb = 12'hFFF; // White
            6'h21: rgb = 12'h3BF; // Sky Blue
            6'h22: rgb = 12'h68F; // Light Blue
            6'h23: rgb = 12'hA7F; // Lavender
            6'h24: rgb = 12'hF6F; // Pink
            6'h25: rgb = 12'hF5A; // Light Red
            6'h26: rgb = 12'hF83; // Light Orange
            6'h27: rgb = 12'hFA4; // Light Yellow-Orange
            6'h28: rgb = 12'hED0; // Yellow
            6'h29: rgb = 12'h9E0; // Light Green
            6'h2A: rgb = 12'h5F5; // Bright Green
            6'h2B: rgb = 12'h4FA; // Aqua
            6'h2C: rgb = 12'h5DD; // Light Cyan
            6'h2D: rgb = 12'h555; // Medium Gray
            6'h2E: rgb = 12'h000; // Black
            6'h2F: rgb = 12'h000; // Black
            
            // Row 3 (pale colors)
            6'h30: rgb = 12'hFFF; // White
            6'h31: rgb = 12'hAEF; // Pale Blue
            6'h32: rgb = 12'hCCF; // Pale Lavender
            6'h33: rgb = 12'hDBF; // Pale Violet
            6'h34: rgb = 12'hFBF; // Pale Pink
            6'h35: rgb = 12'hFAC; // Pale Rose
            6'h36: rgb = 12'hFC9; // Pale Orange
            6'h37: rgb = 12'hFD8; // Pale Yellow
            6'h38: rgb = 12'hFF8; // Light Yellow
            6'h39: rgb = 12'hCF8; // Pale Green
            6'h3A: rgb = 12'hAFB; // Pale Cyan-Green
            6'h3B: rgb = 12'hAFF; // Pale Cyan
            6'h3C: rgb = 12'hBFF; // Pale Sky
            6'h3D: rgb = 12'h888; // Light Gray
            6'h3E: rgb = 12'h000; // Black
            6'h3F: rgb = 12'h000; // Black
            
            default: rgb = 12'h000;
        endcase
    end

endmodule
