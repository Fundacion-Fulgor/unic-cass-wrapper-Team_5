module debug_unit #(
  parameter integer NB_ADDR = 7,
  parameter integer NB_DATA = 8
)(
  `ifdef USE_POWER_PINS
  inout                       VPWR,
  inout                       VGND,
  `endif
  input  wire                 clk,
  input  wire                 rst_n,
  input  wire [NB_ADDR-1:0]   spi_addr,
  input  wire [NB_DATA-1:0]   spi_wdata,
  input  wire                 spi_rw,     // 1=READ, 0=WRITE from spi_slave_mode0
  input  wire                 spi_ss_n,
  output reg  [NB_DATA-1:0]   spi_rdata,
  input  wire [NB_DATA-1:0]   status_flags,
  input  wire [NB_DATA-1:0]   error_flags,
  input  wire [NB_DATA-1:0]   cnt_inputs,
  input  wire [NB_DATA-1:0]   cnt_outputs,
  input  wire [NB_DATA-1:0]   last_out_re,
  input  wire [NB_DATA-1:0]   last_out_im,
  input  wire [NB_DATA-1:0]   mid_data_re,
  output reg  [2:0]           sys_config
);

localparam [NB_ADDR-1:0] ADDR_STATUS_FLAGS = 'h00;
localparam [NB_ADDR-1:0] ADDR_ERROR_FLAGS  = 'h01;
localparam [NB_ADDR-1:0] ADDR_CNT_INPUTS   = 'h02;
localparam [NB_ADDR-1:0] ADDR_CNT_OUTPUTS  = 'h03;
localparam [NB_ADDR-1:0] ADDR_LAST_OUT_RE  = 'h04;
localparam [NB_ADDR-1:0] ADDR_LAST_OUT_IM  = 'h05;
localparam [NB_ADDR-1:0] ADDR_MID_DATA_RE  = 'h06;
localparam [NB_ADDR-1:0] ADDR_SYS_CONFIG   = 'h10;

// ---------------------------------------------------------------------------
// ss_n triple-flop synchronizer
// Falling edge -> snapshot_pulse (status registers captured)
// Rising edge  -> commit_pulse   (write data captured)
// ---------------------------------------------------------------------------

reg [2:0] ss_sync;

always @(posedge clk or negedge rst_n) begin
    if (!rst_n) ss_sync <= 3'b111;
    else        ss_sync <= {ss_sync[1:0], spi_ss_n};
end

wire snapshot_pulse;
wire commit_pulse;
assign snapshot_pulse = (ss_sync[2] == 1'b1) && (ss_sync[1] == 1'b0);
assign commit_pulse   = (ss_sync[2] == 1'b0) && (ss_sync[1] == 1'b1);

// ---------------------------------------------------------------------------
// Capture addr / wdata / rw on commit_pulse (ss_n rising edge)
// rw_bit is stable from the 8th sclk cycle onward — well before ss_n rises
// addr_out and data_out are stable from the last sclk cycle onward
// ---------------------------------------------------------------------------

reg [NB_DATA-1:0] wdata_snap;
reg [NB_ADDR-1:0] addr_snap;
reg               rw_snap;    // 1=READ, 0=WRITE

always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        wdata_snap <= {NB_DATA{1'b0}};
        addr_snap  <= {NB_ADDR{1'b0}};
        rw_snap    <= 1'b1;
    end
    else if (commit_pulse) begin
        wdata_snap <= spi_wdata;
        addr_snap  <= spi_addr;
        rw_snap    <= spi_rw;
    end
end

// ---------------------------------------------------------------------------
// Write sys_config one cycle after commit_pulse so snapped values are stable
// ---------------------------------------------------------------------------

reg commit_pulse_q;
always @(posedge clk or negedge rst_n) begin
    if (!rst_n) commit_pulse_q <= 1'b0;
    else        commit_pulse_q <= commit_pulse;
end

always @(posedge clk or negedge rst_n) begin
    if (!rst_n)
        sys_config <= 3'b000;
    else if (commit_pulse_q && !rw_snap && (addr_snap == ADDR_SYS_CONFIG))
        sys_config <= wdata_snap[2:0];
end

// ---------------------------------------------------------------------------
// CDC Snapshots for probe/status signals — captured on ss_n falling edge
// ---------------------------------------------------------------------------

wire [NB_DATA-1:0] status_flags_sync;
cdc_snapshot #(.DATA_WIDTH(NB_DATA)) u_cdc_status_flags (
  `ifdef USE_POWER_PINS
  .VPWR            (VPWR),  .VGND            (VGND),
  `endif
  .clk             (clk),   .rst_n           (rst_n),
  .trigger_async_n (spi_ss_n),
  .data_in         (status_flags),
  .data_out        (status_flags_sync)
);

wire [NB_DATA-1:0] error_flags_sync;
cdc_snapshot #(.DATA_WIDTH(NB_DATA)) u_cdc_error_flags (
  `ifdef USE_POWER_PINS
  .VPWR            (VPWR),  .VGND            (VGND),
  `endif
  .clk             (clk),   .rst_n           (rst_n),
  .trigger_async_n (spi_ss_n),
  .data_in         (error_flags),
  .data_out        (error_flags_sync)
);

wire [NB_DATA-1:0] cnt_inputs_sync;
cdc_snapshot #(.DATA_WIDTH(NB_DATA)) u_cdc_cnt_inputs (
  `ifdef USE_POWER_PINS
  .VPWR            (VPWR),  .VGND            (VGND),
  `endif
  .clk             (clk),   .rst_n           (rst_n),
  .trigger_async_n (spi_ss_n),
  .data_in         (cnt_inputs),
  .data_out        (cnt_inputs_sync)
);

wire [NB_DATA-1:0] cnt_outputs_sync;
cdc_snapshot #(.DATA_WIDTH(NB_DATA)) u_cdc_cnt_outputs (
  `ifdef USE_POWER_PINS
  .VPWR            (VPWR),  .VGND            (VGND),
  `endif
  .clk             (clk),   .rst_n           (rst_n),
  .trigger_async_n (spi_ss_n),
  .data_in         (cnt_outputs),
  .data_out        (cnt_outputs_sync)
);

wire [NB_DATA-1:0] last_out_re_sync;
cdc_snapshot #(.DATA_WIDTH(NB_DATA)) u_cdc_last_out_re (
  `ifdef USE_POWER_PINS
  .VPWR            (VPWR),  .VGND            (VGND),
  `endif
  .clk             (clk),   .rst_n           (rst_n),
  .trigger_async_n (spi_ss_n),
  .data_in         (last_out_re),
  .data_out        (last_out_re_sync)
);

wire [NB_DATA-1:0] last_out_im_sync;
cdc_snapshot #(.DATA_WIDTH(NB_DATA)) u_cdc_last_out_im (
  `ifdef USE_POWER_PINS
  .VPWR            (VPWR),  .VGND            (VGND),
  `endif
  .clk             (clk),   .rst_n           (rst_n),
  .trigger_async_n (spi_ss_n),
  .data_in         (last_out_im),
  .data_out        (last_out_im_sync)
);

wire [NB_DATA-1:0] mid_data_re_sync;
cdc_snapshot #(.DATA_WIDTH(NB_DATA)) u_cdc_mid_data_re (
  `ifdef USE_POWER_PINS
  .VPWR            (VPWR),  .VGND            (VGND),
  `endif
  .clk             (clk),   .rst_n           (rst_n),
  .trigger_async_n (spi_ss_n),
  .data_in         (mid_data_re),
  .data_out        (mid_data_re_sync)
);

// ---------------------------------------------------------------------------
// Read mux — combinational on spi_addr directly
// ---------------------------------------------------------------------------

always @(*) begin
    case (spi_addr)
        ADDR_STATUS_FLAGS: spi_rdata = status_flags_sync;
        ADDR_ERROR_FLAGS:  spi_rdata = error_flags_sync;
        ADDR_CNT_INPUTS:   spi_rdata = cnt_inputs_sync;
        ADDR_CNT_OUTPUTS:  spi_rdata = cnt_outputs_sync;
        ADDR_LAST_OUT_RE:  spi_rdata = last_out_re_sync;
        ADDR_LAST_OUT_IM:  spi_rdata = last_out_im_sync;
        ADDR_MID_DATA_RE:  spi_rdata = mid_data_re_sync;
        ADDR_SYS_CONFIG:   spi_rdata = {{(NB_DATA-3){1'b0}}, sys_config};
        default:           spi_rdata = {NB_DATA{1'b0}};
    endcase
end

endmodule