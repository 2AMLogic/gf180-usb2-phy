module usb_utmi_phy (Reset,
    RxError,
    RxValid,
    SuspendM,
    TermSelect,
    TxReady,
    TxValid,
    XcvrSelect,
    clk,
    rst_n,
    RxActive,
    rxdm,
    rxdp,
    txdm,
    txdp,
    DataIn,
    DataOut,
    LineState,
    OpMode);
 input Reset;
 output RxError;
 output RxValid;
 input SuspendM;
 input TermSelect;
 output TxReady;
 input TxValid;
 input XcvrSelect;
 input clk;
 input rst_n;
 output RxActive;
 input rxdm;
 input rxdp;
 output txdm;
 output txdp;
 output [7:0] DataIn;
 input [7:0] DataOut;
 output [1:0] LineState;
 input [1:0] OpMode;

 wire _000_;
 wire _001_;
 wire _002_;
 wire _003_;
 wire _004_;
 wire _005_;
 wire _006_;
 wire _007_;
 wire _008_;
 wire _009_;
 wire _010_;
 wire _011_;
 wire _012_;
 wire _013_;
 wire _014_;
 wire _015_;
 wire _016_;
 wire _017_;
 wire _018_;
 wire _019_;
 wire _020_;
 wire _021_;
 wire _022_;
 wire _023_;
 wire _024_;
 wire _025_;
 wire _026_;
 wire _027_;
 wire _028_;
 wire _029_;
 wire _030_;
 wire _031_;
 wire _032_;
 wire _033_;
 wire _034_;
 wire _035_;
 wire _036_;
 wire _037_;
 wire _038_;
 wire _039_;
 wire _040_;
 wire _041_;
 wire _042_;
 wire _043_;
 wire _044_;
 wire _045_;
 wire _046_;
 wire _047_;
 wire _048_;
 wire _049_;
 wire _050_;
 wire _051_;
 wire _052_;
 wire _053_;
 wire _054_;
 wire _055_;
 wire _056_;
 wire _057_;
 wire _058_;
 wire clknet_3_2__leaf_clk;
 wire _060_;
 wire _061_;
 wire clknet_0_clk;
 wire _063_;
 wire _064_;
 wire _065_;
 wire _066_;
 wire _067_;
 wire _068_;
 wire _069_;
 wire _070_;
 wire _071_;
 wire _072_;
 wire _073_;
 wire _074_;
 wire _075_;
 wire _076_;
 wire _077_;
 wire _078_;
 wire clknet_3_4__leaf_clk;
 wire _080_;
 wire clknet_3_1__leaf_clk;
 wire _082_;
 wire _083_;
 wire _084_;
 wire _085_;
 wire _086_;
 wire _087_;
 wire _088_;
 wire _089_;
 wire _090_;
 wire _091_;
 wire _092_;
 wire _093_;
 wire _094_;
 wire _095_;
 wire _096_;
 wire _097_;
 wire _098_;
 wire _099_;
 wire _100_;
 wire _101_;
 wire _102_;
 wire _103_;
 wire _104_;
 wire _105_;
 wire _106_;
 wire _107_;
 wire _108_;
 wire _109_;
 wire _110_;
 wire _111_;
 wire clknet_3_3__leaf_clk;
 wire _113_;
 wire _114_;
 wire clknet_3_0__leaf_clk;
 wire _116_;
 wire _117_;
 wire _118_;
 wire _119_;
 wire _120_;
 wire _121_;
 wire _122_;
 wire _123_;
 wire _124_;
 wire _125_;
 wire _126_;
 wire _127_;
 wire _128_;
 wire _129_;
 wire _130_;
 wire _131_;
 wire _132_;
 wire _133_;
 wire _134_;
 wire _135_;
 wire _136_;
 wire _137_;
 wire _138_;
 wire _139_;
 wire _140_;
 wire _141_;
 wire _142_;
 wire _143_;
 wire _144_;
 wire _145_;
 wire bus_reset;
 wire dec_data_bit;
 wire dec_data_valid;
 wire dec_line_bit;
 wire dec_line_valid;
 wire destuff_in_valid;
 wire destuff_out_bit;
 wire destuff_out_valid;
 wire destuff_stuff_err;
 wire enc_line_bit;
 wire enc_line_valid;
 wire eop_pulse;
 wire int_rst_n;
 wire next_valid;
 wire rx_receiving;
 wire stuff_in_ready;
 wire stuff_out_bit;
 wire stuff_out_valid;
 wire stuffer_in_bit;
 wire stuffer_in_valid;
 wire sync_next;
 wire \u_decoder/_00_ ;
 wire \u_decoder/_01_ ;
 wire \u_decoder/_02_ ;
 wire \u_decoder/_03_ ;
 wire \u_decoder/_04_ ;
 wire \u_decoder/_05_ ;
 wire \u_decoder/_06_ ;
 wire \u_decoder/_07_ ;
 wire \u_decoder/_08_ ;
 wire \u_decoder/prev_line ;
 wire \u_destuffer/_00_ ;
 wire \u_destuffer/_01_ ;
 wire \u_destuffer/_02_ ;
 wire \u_destuffer/_03_ ;
 wire \u_destuffer/_04_ ;
 wire \u_destuffer/_05_ ;
 wire \u_destuffer/_06_ ;
 wire \u_destuffer/_07_ ;
 wire \u_destuffer/_08_ ;
 wire \u_destuffer/_09_ ;
 wire \u_destuffer/_10_ ;
 wire \u_destuffer/_11_ ;
 wire \u_destuffer/_12_ ;
 wire \u_destuffer/_13_ ;
 wire \u_destuffer/_14_ ;
 wire \u_destuffer/_15_ ;
 wire \u_destuffer/_16_ ;
 wire \u_destuffer/_17_ ;
 wire \u_destuffer/_18_ ;
 wire \u_destuffer/_19_ ;
 wire \u_destuffer/_20_ ;
 wire \u_destuffer/_21_ ;
 wire \u_encoder/_00_ ;
 wire \u_encoder/_01_ ;
 wire \u_encoder/_02_ ;
 wire \u_encoder/_03_ ;
 wire \u_encoder/_04_ ;
 wire \u_encoder/_05_ ;
 wire \u_encoder/_06_ ;
 wire \u_eop_detector/_00_ ;
 wire \u_eop_detector/_01_ ;
 wire \u_eop_detector/_02_ ;
 wire \u_eop_detector/_03_ ;
 wire \u_eop_detector/_04_ ;
 wire \u_eop_detector/_05_ ;
 wire \u_eop_detector/_06_ ;
 wire \u_eop_detector/_07_ ;
 wire \u_eop_detector/_08_ ;
 wire \u_eop_detector/_09_ ;
 wire \u_eop_detector/_10_ ;
 wire \u_eop_detector/_11_ ;
 wire \u_eop_detector/_12_ ;
 wire \u_eop_detector/_13_ ;
 wire \u_eop_detector/_14_ ;
 wire \u_eop_detector/_15_ ;
 wire \u_eop_detector/_16_ ;
 wire \u_eop_detector/_17_ ;
 wire \u_eop_detector/_18_ ;
 wire \u_eop_detector/_19_ ;
 wire \u_eop_detector/_20_ ;
 wire \u_eop_detector/_21_ ;
 wire \u_eop_detector/_22_ ;
 wire \u_eop_detector/_23_ ;
 wire \u_eop_detector/_24_ ;
 wire \u_eop_detector/_25_ ;
 wire \u_eop_detector/_26_ ;
 wire \u_line_state/_0_ ;
 wire \u_line_state/_1_ ;
 wire \u_line_state/_2_ ;
 wire \u_stuffer/_00_ ;
 wire \u_stuffer/_01_ ;
 wire \u_stuffer/_02_ ;
 wire \u_stuffer/_03_ ;
 wire \u_stuffer/_04_ ;
 wire \u_stuffer/_05_ ;
 wire \u_stuffer/_06_ ;
 wire \u_stuffer/_07_ ;
 wire \u_stuffer/_08_ ;
 wire \u_stuffer/_09_ ;
 wire \u_stuffer/_10_ ;
 wire \u_stuffer/_11_ ;
 wire \u_stuffer/_12_ ;
 wire \u_stuffer/_13_ ;
 wire \u_stuffer/_14_ ;
 wire \u_stuffer/_15_ ;
 wire \u_stuffer/_16_ ;
 wire \u_stuffer/_17_ ;
 wire \u_stuffer/_18_ ;
 wire \u_stuffer/out_stuffed ;
 wire \u_sync_detector/_00_ ;
 wire \u_sync_detector/_01_ ;
 wire \u_sync_detector/_02_ ;
 wire \u_sync_detector/_03_ ;
 wire \u_sync_detector/_04_ ;
 wire \u_sync_detector/_05_ ;
 wire \u_sync_detector/_06_ ;
 wire \u_sync_detector/_07_ ;
 wire \u_sync_detector/_08_ ;
 wire \u_sync_detector/_09_ ;
 wire \u_sync_detector/_10_ ;
 wire \u_sync_detector/_11_ ;
 wire \u_sync_detector/_12_ ;
 wire \u_sync_detector/_13_ ;
 wire \u_sync_detector/_14_ ;
 wire \u_sync_detector/_15_ ;
 wire \u_sync_detector/sync_valid ;
 wire clknet_3_5__leaf_clk;
 wire clknet_3_6__leaf_clk;
 wire clknet_3_7__leaf_clk;
 wire [7:0] cur_byte;
 wire [1:0] line_state;
 wire [7:0] next_byte;
 wire [2:0] rx_bitcnt;
 wire [7:0] rx_shift;
 wire [2:0] tx_bitidx;
 wire [8:0] tx_state;
 wire [2:0] \u_destuffer/ones ;
 wire [5:0] \u_eop_detector/se0_count ;
 wire [2:0] \u_stuffer/ones ;
 wire [3:0] \u_sync_detector/match ;

 gf180mcu_fd_sc_mcu9t5v0__inv_1 _146_ (.I(rx_receiving),
    .ZN(_009_));
 gf180mcu_fd_sc_mcu9t5v0__inv_1 _147_ (.I(rst_n),
    .ZN(_053_));
 gf180mcu_fd_sc_mcu9t5v0__or2_2 _148_ (.A1(_053_),
    .A2(Reset),
    .Z(_054_));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_1 _149_ (.I(_054_),
    .ZN(int_rst_n));
 gf180mcu_fd_sc_mcu9t5v0__and4_4 _150_ (.A1(tx_bitidx[0]),
    .A2(tx_bitidx[2]),
    .A3(tx_bitidx[1]),
    .A4(stuff_in_ready),
    .Z(_055_));
 gf180mcu_fd_sc_mcu9t5v0__inv_3 _151_ (.I(tx_state[3]),
    .ZN(_056_));
 gf180mcu_fd_sc_mcu9t5v0__nor2_4 _152_ (.A1(next_valid),
    .A2(_056_),
    .ZN(_057_));
 gf180mcu_fd_sc_mcu9t5v0__and3_1 _153_ (.A1(int_rst_n),
    .A2(_055_),
    .A3(_057_),
    .Z(_005_));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_1 _154_ (.I(tx_state[7]),
    .ZN(_058_));
 gf180mcu_fd_sc_mcu9t5v0__nor2_1 _156_ (.A1(_058_),
    .A2(_054_),
    .ZN(_001_));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_1 _157_ (.I(tx_state[5]),
    .ZN(_060_));
 gf180mcu_fd_sc_mcu9t5v0__nand4_1 _158_ (.A1(tx_bitidx[0]),
    .A2(tx_bitidx[2]),
    .A3(tx_bitidx[1]),
    .A4(stuff_in_ready),
    .ZN(_061_));
 gf180mcu_fd_sc_mcu9t5v0__oai21_1 _160_ (.A1(next_valid),
    .A2(_061_),
    .B(tx_state[3]),
    .ZN(_063_));
 gf180mcu_fd_sc_mcu9t5v0__aoi21_1 _161_ (.A1(_060_),
    .A2(_063_),
    .B(_054_),
    .ZN(_008_));
 gf180mcu_fd_sc_mcu9t5v0__and3_1 _162_ (.A1(tx_state[0]),
    .A2(TxValid),
    .A3(int_rst_n),
    .Z(_003_));
 gf180mcu_fd_sc_mcu9t5v0__and2_1 _163_ (.A1(tx_state[4]),
    .A2(int_rst_n),
    .Z(_006_));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_1 _164_ (.I(tx_state[0]),
    .ZN(_064_));
 gf180mcu_fd_sc_mcu9t5v0__nor2_1 _165_ (.A1(tx_state[1]),
    .A2(_054_),
    .ZN(_065_));
 gf180mcu_fd_sc_mcu9t5v0__oai21_1 _166_ (.A1(_064_),
    .A2(TxValid),
    .B(_065_),
    .ZN(_007_));
 gf180mcu_fd_sc_mcu9t5v0__and2_1 _167_ (.A1(tx_state[2]),
    .A2(int_rst_n),
    .Z(_004_));
 gf180mcu_fd_sc_mcu9t5v0__and2_1 _168_ (.A1(tx_state[6]),
    .A2(int_rst_n),
    .Z(_002_));
 gf180mcu_fd_sc_mcu9t5v0__and2_1 _169_ (.A1(rx_receiving),
    .A2(dec_data_valid),
    .Z(destuff_in_valid));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_1 _170_ (.I(line_state[0]),
    .ZN(_066_));
 gf180mcu_fd_sc_mcu9t5v0__nor2_1 _171_ (.A1(_066_),
    .A2(line_state[1]),
    .ZN(dec_line_bit));
 gf180mcu_fd_sc_mcu9t5v0__xor2_1 _172_ (.A1(line_state[0]),
    .A2(line_state[1]),
    .Z(dec_line_valid));
 gf180mcu_fd_sc_mcu9t5v0__aoi21_1 _173_ (.A1(tx_state[3]),
    .A2(_055_),
    .B(tx_state[0]),
    .ZN(_067_));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_1 _174_ (.I(_067_),
    .ZN(TxReady));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_1 _175_ (.I(cur_byte[3]),
    .ZN(_068_));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_1 _176_ (.I(cur_byte[7]),
    .ZN(_069_));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_1 _177_ (.I(cur_byte[1]),
    .ZN(_070_));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_1 _178_ (.I(cur_byte[5]),
    .ZN(_071_));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_1 _179_ (.I(tx_bitidx[1]),
    .ZN(_072_));
 gf180mcu_fd_sc_mcu9t5v0__mux4_1 _180_ (.I0(_068_),
    .I1(_069_),
    .I2(_070_),
    .I3(_071_),
    .S0(tx_bitidx[2]),
    .S1(_072_),
    .Z(_073_));
 gf180mcu_fd_sc_mcu9t5v0__mux4_1 _181_ (.I0(cur_byte[0]),
    .I1(cur_byte[4]),
    .I2(cur_byte[2]),
    .I3(cur_byte[6]),
    .S0(tx_bitidx[2]),
    .S1(tx_bitidx[1]),
    .Z(_074_));
 gf180mcu_fd_sc_mcu9t5v0__nor2_1 _182_ (.A1(tx_bitidx[0]),
    .A2(_074_),
    .ZN(_075_));
 gf180mcu_fd_sc_mcu9t5v0__aoi211_1 _183_ (.A1(tx_bitidx[0]),
    .A2(_073_),
    .B(_075_),
    .C(_056_),
    .ZN(stuffer_in_bit));
 gf180mcu_fd_sc_mcu9t5v0__oai21_1 _184_ (.A1(stuff_in_ready),
    .A2(_058_),
    .B(_056_),
    .ZN(stuffer_in_valid));
 gf180mcu_fd_sc_mcu9t5v0__and2_1 _185_ (.A1(tx_state[8]),
    .A2(int_rst_n),
    .Z(_000_));
 gf180mcu_fd_sc_mcu9t5v0__mux2_2 _186_ (.I0(tx_state[3]),
    .I1(TxValid),
    .S(tx_state[0]),
    .Z(_076_));
 gf180mcu_fd_sc_mcu9t5v0__oai21_4 _187_ (.A1(_056_),
    .A2(_055_),
    .B(_076_),
    .ZN(_077_));
 gf180mcu_fd_sc_mcu9t5v0__or2_2 _188_ (.A1(_057_),
    .A2(_077_),
    .Z(_078_));
 gf180mcu_fd_sc_mcu9t5v0__aoi211_2 _190_ (.A1(next_byte[1]),
    .A2(tx_state[3]),
    .B(_057_),
    .C(_077_),
    .ZN(_080_));
 gf180mcu_fd_sc_mcu9t5v0__aoi211_2 _192_ (.A1(_070_),
    .A2(_078_),
    .B(_080_),
    .C(_054_),
    .ZN(_010_));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_1 _193_ (.I(cur_byte[0]),
    .ZN(_082_));
 gf180mcu_fd_sc_mcu9t5v0__aoi211_2 _194_ (.A1(next_byte[0]),
    .A2(tx_state[3]),
    .B(_057_),
    .C(_077_),
    .ZN(_083_));
 gf180mcu_fd_sc_mcu9t5v0__aoi211_2 _195_ (.A1(_082_),
    .A2(_078_),
    .B(_083_),
    .C(_054_),
    .ZN(_011_));
 gf180mcu_fd_sc_mcu9t5v0__oai21_1 _196_ (.A1(tx_state[3]),
    .A2(tx_state[0]),
    .B(TxValid),
    .ZN(_084_));
 gf180mcu_fd_sc_mcu9t5v0__aoi21_2 _197_ (.A1(tx_state[3]),
    .A2(_061_),
    .B(_084_),
    .ZN(_085_));
 gf180mcu_fd_sc_mcu9t5v0__nand2_1 _198_ (.A1(DataOut[6]),
    .A2(_085_),
    .ZN(_086_));
 gf180mcu_fd_sc_mcu9t5v0__or2_1 _199_ (.A1(tx_state[3]),
    .A2(tx_state[0]),
    .Z(_087_));
 gf180mcu_fd_sc_mcu9t5v0__oai211_2 _200_ (.A1(_056_),
    .A2(_055_),
    .B(_087_),
    .C(TxValid),
    .ZN(_088_));
 gf180mcu_fd_sc_mcu9t5v0__nand2_1 _201_ (.A1(next_byte[6]),
    .A2(_088_),
    .ZN(_089_));
 gf180mcu_fd_sc_mcu9t5v0__aoi21_1 _202_ (.A1(_086_),
    .A2(_089_),
    .B(_054_),
    .ZN(_012_));
 gf180mcu_fd_sc_mcu9t5v0__nand2_1 _203_ (.A1(DataOut[5]),
    .A2(_085_),
    .ZN(_090_));
 gf180mcu_fd_sc_mcu9t5v0__nand2_1 _204_ (.A1(next_byte[5]),
    .A2(_088_),
    .ZN(_091_));
 gf180mcu_fd_sc_mcu9t5v0__aoi21_1 _205_ (.A1(_090_),
    .A2(_091_),
    .B(_054_),
    .ZN(_013_));
 gf180mcu_fd_sc_mcu9t5v0__nand2_1 _206_ (.A1(DataOut[4]),
    .A2(_085_),
    .ZN(_092_));
 gf180mcu_fd_sc_mcu9t5v0__nand2_1 _207_ (.A1(next_byte[4]),
    .A2(_088_),
    .ZN(_093_));
 gf180mcu_fd_sc_mcu9t5v0__aoi21_1 _208_ (.A1(_092_),
    .A2(_093_),
    .B(_054_),
    .ZN(_014_));
 gf180mcu_fd_sc_mcu9t5v0__nand2_1 _209_ (.A1(DataOut[3]),
    .A2(_085_),
    .ZN(_094_));
 gf180mcu_fd_sc_mcu9t5v0__nand2_1 _210_ (.A1(next_byte[3]),
    .A2(_088_),
    .ZN(_095_));
 gf180mcu_fd_sc_mcu9t5v0__aoi21_1 _211_ (.A1(_094_),
    .A2(_095_),
    .B(_054_),
    .ZN(_015_));
 gf180mcu_fd_sc_mcu9t5v0__nand2_1 _212_ (.A1(DataOut[2]),
    .A2(_085_),
    .ZN(_096_));
 gf180mcu_fd_sc_mcu9t5v0__nand2_1 _213_ (.A1(next_byte[2]),
    .A2(_088_),
    .ZN(_097_));
 gf180mcu_fd_sc_mcu9t5v0__aoi21_1 _214_ (.A1(_096_),
    .A2(_097_),
    .B(_054_),
    .ZN(_016_));
 gf180mcu_fd_sc_mcu9t5v0__nand2_1 _215_ (.A1(DataOut[1]),
    .A2(_085_),
    .ZN(_098_));
 gf180mcu_fd_sc_mcu9t5v0__nand2_1 _216_ (.A1(next_byte[1]),
    .A2(_088_),
    .ZN(_099_));
 gf180mcu_fd_sc_mcu9t5v0__aoi21_1 _217_ (.A1(_098_),
    .A2(_099_),
    .B(_054_),
    .ZN(_017_));
 gf180mcu_fd_sc_mcu9t5v0__nand2_1 _218_ (.A1(DataOut[0]),
    .A2(_085_),
    .ZN(_100_));
 gf180mcu_fd_sc_mcu9t5v0__nand2_1 _219_ (.A1(next_byte[0]),
    .A2(_088_),
    .ZN(_101_));
 gf180mcu_fd_sc_mcu9t5v0__aoi21_1 _220_ (.A1(_100_),
    .A2(_101_),
    .B(_054_),
    .ZN(_018_));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_1 _221_ (.I(tx_bitidx[0]),
    .ZN(_102_));
 gf180mcu_fd_sc_mcu9t5v0__oai21_1 _222_ (.A1(_056_),
    .A2(stuff_in_ready),
    .B(_076_),
    .ZN(_103_));
 gf180mcu_fd_sc_mcu9t5v0__or2_2 _223_ (.A1(_102_),
    .A2(_103_),
    .Z(_104_));
 gf180mcu_fd_sc_mcu9t5v0__nand2_1 _224_ (.A1(tx_bitidx[0]),
    .A2(tx_bitidx[1]),
    .ZN(_105_));
 gf180mcu_fd_sc_mcu9t5v0__aoi21_1 _225_ (.A1(tx_state[3]),
    .A2(_105_),
    .B(_103_),
    .ZN(_106_));
 gf180mcu_fd_sc_mcu9t5v0__aoi211_2 _226_ (.A1(_072_),
    .A2(_104_),
    .B(_106_),
    .C(_054_),
    .ZN(_019_));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_1 _227_ (.I(tx_bitidx[2]),
    .ZN(_107_));
 gf180mcu_fd_sc_mcu9t5v0__oai21_1 _228_ (.A1(_105_),
    .A2(_103_),
    .B(_107_),
    .ZN(_108_));
 gf180mcu_fd_sc_mcu9t5v0__and3_1 _229_ (.A1(int_rst_n),
    .A2(_077_),
    .A3(_108_),
    .Z(_020_));
 gf180mcu_fd_sc_mcu9t5v0__oai21_1 _230_ (.A1(_056_),
    .A2(_103_),
    .B(_102_),
    .ZN(_109_));
 gf180mcu_fd_sc_mcu9t5v0__and3_1 _231_ (.A1(int_rst_n),
    .A2(_104_),
    .A3(_109_),
    .Z(_021_));
 gf180mcu_fd_sc_mcu9t5v0__and3_1 _232_ (.A1(rx_bitcnt[0]),
    .A2(destuff_out_valid),
    .A3(rx_bitcnt[1]),
    .Z(_110_));
 gf180mcu_fd_sc_mcu9t5v0__nor3_2 _233_ (.A1(_009_),
    .A2(_053_),
    .A3(Reset),
    .ZN(_111_));
 gf180mcu_fd_sc_mcu9t5v0__oai21_1 _235_ (.A1(rx_bitcnt[2]),
    .A2(_110_),
    .B(_111_),
    .ZN(_113_));
 gf180mcu_fd_sc_mcu9t5v0__aoi21_1 _236_ (.A1(rx_bitcnt[2]),
    .A2(_110_),
    .B(_113_),
    .ZN(_022_));
 gf180mcu_fd_sc_mcu9t5v0__nand3_2 _237_ (.A1(rx_bitcnt[2]),
    .A2(_110_),
    .A3(_111_),
    .ZN(_114_));
 gf180mcu_fd_sc_mcu9t5v0__mux2_1 _238_ (.I0(rx_shift[7]),
    .I1(DataIn[6]),
    .S(_114_),
    .Z(_023_));
 gf180mcu_fd_sc_mcu9t5v0__mux2_1 _240_ (.I0(rx_shift[7]),
    .I1(destuff_out_bit),
    .S(destuff_out_valid),
    .Z(_116_));
 gf180mcu_fd_sc_mcu9t5v0__and2_1 _241_ (.A1(_111_),
    .A2(_116_),
    .Z(_024_));
 gf180mcu_fd_sc_mcu9t5v0__mux2_1 _242_ (.I0(rx_shift[6]),
    .I1(DataIn[5]),
    .S(_114_),
    .Z(_025_));
 gf180mcu_fd_sc_mcu9t5v0__nor4_2 _243_ (.A1(next_byte[7]),
    .A2(_056_),
    .A3(_057_),
    .A4(_077_),
    .ZN(_117_));
 gf180mcu_fd_sc_mcu9t5v0__aoi211_2 _244_ (.A1(_069_),
    .A2(_078_),
    .B(_117_),
    .C(_054_),
    .ZN(_026_));
 gf180mcu_fd_sc_mcu9t5v0__mux2_1 _245_ (.I0(rx_shift[5]),
    .I1(DataIn[4]),
    .S(_114_),
    .Z(_027_));
 gf180mcu_fd_sc_mcu9t5v0__mux2_1 _246_ (.I0(rx_shift[4]),
    .I1(DataIn[3]),
    .S(_114_),
    .Z(_028_));
 gf180mcu_fd_sc_mcu9t5v0__mux2_1 _247_ (.I0(rx_shift[3]),
    .I1(DataIn[2]),
    .S(_114_),
    .Z(_029_));
 gf180mcu_fd_sc_mcu9t5v0__mux2_1 _248_ (.I0(destuff_out_bit),
    .I1(DataIn[7]),
    .S(_114_),
    .Z(_030_));
 gf180mcu_fd_sc_mcu9t5v0__mux2_1 _249_ (.I0(rx_shift[2]),
    .I1(DataIn[1]),
    .S(_114_),
    .Z(_031_));
 gf180mcu_fd_sc_mcu9t5v0__nor2_1 _250_ (.A1(tx_state[4]),
    .A2(tx_state[8]),
    .ZN(_118_));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_1 _251_ (.I(txdp),
    .ZN(_119_));
 gf180mcu_fd_sc_mcu9t5v0__nand2_1 _252_ (.A1(enc_line_valid),
    .A2(enc_line_bit),
    .ZN(_120_));
 gf180mcu_fd_sc_mcu9t5v0__oai21_1 _253_ (.A1(enc_line_valid),
    .A2(_119_),
    .B(_120_),
    .ZN(_121_));
 gf180mcu_fd_sc_mcu9t5v0__nand2_1 _254_ (.A1(_118_),
    .A2(_121_),
    .ZN(_122_));
 gf180mcu_fd_sc_mcu9t5v0__nand2_1 _255_ (.A1(_065_),
    .A2(_122_),
    .ZN(_032_));
 gf180mcu_fd_sc_mcu9t5v0__mux2_1 _256_ (.I0(rx_shift[1]),
    .I1(DataIn[0]),
    .S(_114_),
    .Z(_033_));
 gf180mcu_fd_sc_mcu9t5v0__nand2_1 _257_ (.A1(DataOut[7]),
    .A2(_085_),
    .ZN(_123_));
 gf180mcu_fd_sc_mcu9t5v0__nand2_1 _258_ (.A1(next_byte[7]),
    .A2(_088_),
    .ZN(_124_));
 gf180mcu_fd_sc_mcu9t5v0__aoi21_1 _259_ (.A1(_123_),
    .A2(_124_),
    .B(_054_),
    .ZN(_034_));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_1 _260_ (.I(_114_),
    .ZN(_035_));
 gf180mcu_fd_sc_mcu9t5v0__nand2_1 _261_ (.A1(next_valid),
    .A2(_077_),
    .ZN(_125_));
 gf180mcu_fd_sc_mcu9t5v0__aoi21_1 _262_ (.A1(_088_),
    .A2(_125_),
    .B(_054_),
    .ZN(_036_));
 gf180mcu_fd_sc_mcu9t5v0__mux2_1 _263_ (.I0(rx_shift[6]),
    .I1(rx_shift[7]),
    .S(destuff_out_valid),
    .Z(_126_));
 gf180mcu_fd_sc_mcu9t5v0__and2_1 _264_ (.A1(_111_),
    .A2(_126_),
    .Z(_037_));
 gf180mcu_fd_sc_mcu9t5v0__mux2_1 _265_ (.I0(rx_shift[5]),
    .I1(rx_shift[6]),
    .S(destuff_out_valid),
    .Z(_127_));
 gf180mcu_fd_sc_mcu9t5v0__and2_1 _266_ (.A1(_111_),
    .A2(_127_),
    .Z(_038_));
 gf180mcu_fd_sc_mcu9t5v0__mux2_1 _267_ (.I0(rx_shift[4]),
    .I1(rx_shift[5]),
    .S(destuff_out_valid),
    .Z(_128_));
 gf180mcu_fd_sc_mcu9t5v0__and2_1 _268_ (.A1(_111_),
    .A2(_128_),
    .Z(_039_));
 gf180mcu_fd_sc_mcu9t5v0__mux2_1 _269_ (.I0(rx_shift[3]),
    .I1(rx_shift[4]),
    .S(destuff_out_valid),
    .Z(_129_));
 gf180mcu_fd_sc_mcu9t5v0__and2_1 _270_ (.A1(_111_),
    .A2(_129_),
    .Z(_040_));
 gf180mcu_fd_sc_mcu9t5v0__and2_1 _271_ (.A1(destuff_stuff_err),
    .A2(_111_),
    .Z(_041_));
 gf180mcu_fd_sc_mcu9t5v0__mux2_1 _272_ (.I0(rx_shift[2]),
    .I1(rx_shift[3]),
    .S(destuff_out_valid),
    .Z(_130_));
 gf180mcu_fd_sc_mcu9t5v0__and2_1 _273_ (.A1(_111_),
    .A2(_130_),
    .Z(_042_));
 gf180mcu_fd_sc_mcu9t5v0__mux2_1 _274_ (.I0(rx_shift[1]),
    .I1(rx_shift[2]),
    .S(destuff_out_valid),
    .Z(_131_));
 gf180mcu_fd_sc_mcu9t5v0__and2_1 _275_ (.A1(_111_),
    .A2(_131_),
    .Z(_043_));
 gf180mcu_fd_sc_mcu9t5v0__oai211_1 _276_ (.A1(txdm),
    .A2(enc_line_valid),
    .B(_118_),
    .C(_120_),
    .ZN(_132_));
 gf180mcu_fd_sc_mcu9t5v0__nor3_1 _277_ (.A1(tx_state[1]),
    .A2(_054_),
    .A3(_132_),
    .ZN(_044_));
 gf180mcu_fd_sc_mcu9t5v0__aoi21_1 _278_ (.A1(rx_bitcnt[0]),
    .A2(destuff_out_valid),
    .B(rx_bitcnt[1]),
    .ZN(_133_));
 gf180mcu_fd_sc_mcu9t5v0__nor4_1 _279_ (.A1(_009_),
    .A2(_054_),
    .A3(_110_),
    .A4(_133_),
    .ZN(_045_));
 gf180mcu_fd_sc_mcu9t5v0__oai21_1 _280_ (.A1(rx_bitcnt[0]),
    .A2(destuff_out_valid),
    .B(_111_),
    .ZN(_134_));
 gf180mcu_fd_sc_mcu9t5v0__aoi21_1 _281_ (.A1(rx_bitcnt[0]),
    .A2(destuff_out_valid),
    .B(_134_),
    .ZN(_046_));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_1 _282_ (.I(cur_byte[6]),
    .ZN(_135_));
 gf180mcu_fd_sc_mcu9t5v0__aoi211_2 _283_ (.A1(next_byte[6]),
    .A2(tx_state[3]),
    .B(_057_),
    .C(_077_),
    .ZN(_136_));
 gf180mcu_fd_sc_mcu9t5v0__aoi211_2 _284_ (.A1(_135_),
    .A2(_078_),
    .B(_136_),
    .C(_054_),
    .ZN(_047_));
 gf180mcu_fd_sc_mcu9t5v0__aoi211_2 _285_ (.A1(next_byte[5]),
    .A2(tx_state[3]),
    .B(_057_),
    .C(_077_),
    .ZN(_137_));
 gf180mcu_fd_sc_mcu9t5v0__aoi211_2 _286_ (.A1(_071_),
    .A2(_078_),
    .B(_137_),
    .C(_054_),
    .ZN(_048_));
 gf180mcu_fd_sc_mcu9t5v0__nor3_1 _287_ (.A1(_009_),
    .A2(eop_pulse),
    .A3(bus_reset),
    .ZN(_138_));
 gf180mcu_fd_sc_mcu9t5v0__nor2_1 _288_ (.A1(sync_next),
    .A2(_138_),
    .ZN(_139_));
 gf180mcu_fd_sc_mcu9t5v0__nor2_1 _289_ (.A1(_054_),
    .A2(_139_),
    .ZN(_049_));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_1 _290_ (.I(cur_byte[4]),
    .ZN(_140_));
 gf180mcu_fd_sc_mcu9t5v0__aoi211_2 _291_ (.A1(next_byte[4]),
    .A2(tx_state[3]),
    .B(_057_),
    .C(_077_),
    .ZN(_141_));
 gf180mcu_fd_sc_mcu9t5v0__aoi211_2 _292_ (.A1(_140_),
    .A2(_078_),
    .B(_141_),
    .C(_054_),
    .ZN(_050_));
 gf180mcu_fd_sc_mcu9t5v0__aoi211_2 _293_ (.A1(next_byte[3]),
    .A2(tx_state[3]),
    .B(_057_),
    .C(_077_),
    .ZN(_142_));
 gf180mcu_fd_sc_mcu9t5v0__aoi211_2 _294_ (.A1(_068_),
    .A2(_078_),
    .B(_142_),
    .C(_054_),
    .ZN(_051_));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_1 _295_ (.I(cur_byte[2]),
    .ZN(_143_));
 gf180mcu_fd_sc_mcu9t5v0__aoi211_2 _296_ (.A1(next_byte[2]),
    .A2(tx_state[3]),
    .B(_057_),
    .C(_077_),
    .ZN(_144_));
 gf180mcu_fd_sc_mcu9t5v0__aoi211_2 _297_ (.A1(_143_),
    .A2(_078_),
    .B(_144_),
    .C(_054_),
    .ZN(_052_));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _298_ (.D(_018_),
    .CLK(clknet_3_4__leaf_clk),
    .Q(next_byte[0]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _299_ (.D(_017_),
    .CLK(clknet_3_4__leaf_clk),
    .Q(next_byte[1]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _300_ (.D(_016_),
    .CLK(clknet_3_4__leaf_clk),
    .Q(next_byte[2]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _301_ (.D(_015_),
    .CLK(clknet_3_5__leaf_clk),
    .Q(next_byte[3]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _302_ (.D(_014_),
    .CLK(clknet_3_4__leaf_clk),
    .Q(next_byte[4]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _303_ (.D(_013_),
    .CLK(clknet_3_4__leaf_clk),
    .Q(next_byte[5]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _304_ (.D(_012_),
    .CLK(clknet_3_4__leaf_clk),
    .Q(next_byte[6]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _305_ (.D(_034_),
    .CLK(clknet_3_4__leaf_clk),
    .Q(next_byte[7]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _306_ (.D(_046_),
    .CLK(clknet_3_0__leaf_clk),
    .Q(rx_bitcnt[0]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _307_ (.D(_045_),
    .CLK(clknet_3_0__leaf_clk),
    .Q(rx_bitcnt[1]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _308_ (.D(_022_),
    .CLK(clknet_3_0__leaf_clk),
    .Q(rx_bitcnt[2]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _309_ (.D(_043_),
    .CLK(clknet_3_1__leaf_clk),
    .Q(rx_shift[1]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _310_ (.D(_042_),
    .CLK(clknet_3_1__leaf_clk),
    .Q(rx_shift[2]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _311_ (.D(_040_),
    .CLK(clknet_3_1__leaf_clk),
    .Q(rx_shift[3]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _312_ (.D(_039_),
    .CLK(clknet_3_0__leaf_clk),
    .Q(rx_shift[4]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _313_ (.D(_038_),
    .CLK(clknet_3_0__leaf_clk),
    .Q(rx_shift[5]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _314_ (.D(_037_),
    .CLK(clknet_3_0__leaf_clk),
    .Q(rx_shift[6]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _315_ (.D(_024_),
    .CLK(clknet_3_0__leaf_clk),
    .Q(rx_shift[7]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _316_ (.D(_033_),
    .CLK(clknet_3_1__leaf_clk),
    .Q(DataIn[0]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _317_ (.D(_031_),
    .CLK(clknet_3_1__leaf_clk),
    .Q(DataIn[1]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _318_ (.D(_029_),
    .CLK(clknet_3_1__leaf_clk),
    .Q(DataIn[2]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _319_ (.D(_028_),
    .CLK(clknet_3_1__leaf_clk),
    .Q(DataIn[3]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _320_ (.D(_027_),
    .CLK(clknet_3_0__leaf_clk),
    .Q(DataIn[4]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _321_ (.D(_025_),
    .CLK(clknet_3_0__leaf_clk),
    .Q(DataIn[5]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _322_ (.D(_023_),
    .CLK(clknet_3_0__leaf_clk),
    .Q(DataIn[6]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _323_ (.D(_030_),
    .CLK(clknet_3_0__leaf_clk),
    .Q(DataIn[7]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _324_ (.D(_035_),
    .CLK(clknet_3_1__leaf_clk),
    .Q(RxValid));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _325_ (.D(_041_),
    .CLK(clknet_3_1__leaf_clk),
    .Q(RxError));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _326_ (.D(_049_),
    .CLK(clknet_3_3__leaf_clk),
    .Q(rx_receiving));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _327_ (.D(_021_),
    .CLK(clknet_3_7__leaf_clk),
    .Q(tx_bitidx[0]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _328_ (.D(_019_),
    .CLK(clknet_3_7__leaf_clk),
    .Q(tx_bitidx[1]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _329_ (.D(_020_),
    .CLK(clknet_3_5__leaf_clk),
    .Q(tx_bitidx[2]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _330_ (.D(_011_),
    .CLK(clknet_3_5__leaf_clk),
    .Q(cur_byte[0]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _331_ (.D(_010_),
    .CLK(clknet_3_5__leaf_clk),
    .Q(cur_byte[1]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _332_ (.D(_052_),
    .CLK(clknet_3_5__leaf_clk),
    .Q(cur_byte[2]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _333_ (.D(_051_),
    .CLK(clknet_3_5__leaf_clk),
    .Q(cur_byte[3]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _334_ (.D(_050_),
    .CLK(clknet_3_5__leaf_clk),
    .Q(cur_byte[4]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _335_ (.D(_048_),
    .CLK(clknet_3_5__leaf_clk),
    .Q(cur_byte[5]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _336_ (.D(_047_),
    .CLK(clknet_3_5__leaf_clk),
    .Q(cur_byte[6]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _337_ (.D(_026_),
    .CLK(clknet_3_5__leaf_clk),
    .Q(cur_byte[7]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _338_ (.D(_032_),
    .CLK(clknet_3_3__leaf_clk),
    .Q(txdp));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _339_ (.D(_036_),
    .CLK(clknet_3_5__leaf_clk),
    .Q(next_valid));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _340_ (.D(_044_),
    .CLK(clknet_3_3__leaf_clk),
    .Q(txdm));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _341_ (.D(_007_),
    .CLK(clknet_3_6__leaf_clk),
    .Q(tx_state[0]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _342_ (.D(_000_),
    .CLK(clknet_3_3__leaf_clk),
    .Q(tx_state[1]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _343_ (.D(_001_),
    .CLK(clknet_3_7__leaf_clk),
    .Q(tx_state[2]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _344_ (.D(_008_),
    .CLK(clknet_3_7__leaf_clk),
    .Q(tx_state[3]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _345_ (.D(_002_),
    .CLK(clknet_3_6__leaf_clk),
    .Q(tx_state[4]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _346_ (.D(_003_),
    .CLK(clknet_3_6__leaf_clk),
    .Q(tx_state[5]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _347_ (.D(_004_),
    .CLK(clknet_3_6__leaf_clk),
    .Q(tx_state[6]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _348_ (.D(_005_),
    .CLK(clknet_3_7__leaf_clk),
    .Q(tx_state[7]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _349_ (.D(_006_),
    .CLK(clknet_3_3__leaf_clk),
    .Q(tx_state[8]));
 gf180mcu_fd_sc_mcu9t5v0__tiel _350_ (.ZN(_145_));
 gf180mcu_fd_sc_mcu9t5v0__buf_4 clkbuf_0_clk (.I(clk),
    .Z(clknet_0_clk));
 gf180mcu_fd_sc_mcu9t5v0__buf_4 clkbuf_3_0__f_clk (.I(clknet_0_clk),
    .Z(clknet_3_0__leaf_clk));
 gf180mcu_fd_sc_mcu9t5v0__buf_4 clkbuf_3_1__f_clk (.I(clknet_0_clk),
    .Z(clknet_3_1__leaf_clk));
 gf180mcu_fd_sc_mcu9t5v0__buf_4 clkbuf_3_2__f_clk (.I(clknet_0_clk),
    .Z(clknet_3_2__leaf_clk));
 gf180mcu_fd_sc_mcu9t5v0__buf_4 clkbuf_3_3__f_clk (.I(clknet_0_clk),
    .Z(clknet_3_3__leaf_clk));
 gf180mcu_fd_sc_mcu9t5v0__buf_4 clkbuf_3_4__f_clk (.I(clknet_0_clk),
    .Z(clknet_3_4__leaf_clk));
 gf180mcu_fd_sc_mcu9t5v0__buf_4 clkbuf_3_5__f_clk (.I(clknet_0_clk),
    .Z(clknet_3_5__leaf_clk));
 gf180mcu_fd_sc_mcu9t5v0__buf_4 clkbuf_3_6__f_clk (.I(clknet_0_clk),
    .Z(clknet_3_6__leaf_clk));
 gf180mcu_fd_sc_mcu9t5v0__buf_4 clkbuf_3_7__f_clk (.I(clknet_0_clk),
    .Z(clknet_3_7__leaf_clk));
 gf180mcu_fd_sc_mcu9t5v0__inv_4 clkload0 (.I(clknet_3_1__leaf_clk));
 gf180mcu_fd_sc_mcu9t5v0__inv_3 clkload1 (.I(clknet_3_2__leaf_clk));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_3 clkload2 (.I(clknet_3_3__leaf_clk));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_8 clkload3 (.I(clknet_3_4__leaf_clk));
 gf180mcu_fd_sc_mcu9t5v0__inv_3 clkload4 (.I(clknet_3_5__leaf_clk));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_8 clkload5 (.I(clknet_3_6__leaf_clk));
 gf180mcu_fd_sc_mcu9t5v0__inv_4 clkload6 (.I(clknet_3_7__leaf_clk));
 gf180mcu_fd_sc_mcu9t5v0__xor2_2 \u_decoder/_09_  (.A1(\u_decoder/prev_line ),
    .A2(dec_line_bit),
    .Z(\u_decoder/_03_ ));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_1 \u_decoder/_10_  (.I(_145_),
    .ZN(\u_decoder/_04_ ));
 gf180mcu_fd_sc_mcu9t5v0__oai211_1 \u_decoder/_11_  (.A1(dec_line_valid),
    .A2(dec_data_bit),
    .B(\u_decoder/_04_ ),
    .C(int_rst_n),
    .ZN(\u_decoder/_05_ ));
 gf180mcu_fd_sc_mcu9t5v0__aoi21_2 \u_decoder/_12_  (.A1(dec_line_valid),
    .A2(\u_decoder/_03_ ),
    .B(\u_decoder/_05_ ),
    .ZN(\u_decoder/_00_ ));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_1 \u_decoder/_13_  (.I(\u_decoder/prev_line ),
    .ZN(\u_decoder/_06_ ));
 gf180mcu_fd_sc_mcu9t5v0__and2_1 \u_decoder/_14_  (.A1(\u_decoder/_04_ ),
    .A2(int_rst_n),
    .Z(\u_decoder/_07_ ));
 gf180mcu_fd_sc_mcu9t5v0__nand2_1 \u_decoder/_15_  (.A1(dec_line_bit),
    .A2(dec_line_valid),
    .ZN(\u_decoder/_08_ ));
 gf180mcu_fd_sc_mcu9t5v0__oai211_1 \u_decoder/_16_  (.A1(\u_decoder/_06_ ),
    .A2(dec_line_valid),
    .B(\u_decoder/_07_ ),
    .C(\u_decoder/_08_ ),
    .ZN(\u_decoder/_01_ ));
 gf180mcu_fd_sc_mcu9t5v0__and2_1 \u_decoder/_17_  (.A1(dec_line_valid),
    .A2(\u_decoder/_07_ ),
    .Z(\u_decoder/_02_ ));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 \u_decoder/_18_  (.D(\u_decoder/_01_ ),
    .CLK(clknet_3_3__leaf_clk),
    .Q(\u_decoder/prev_line ));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 \u_decoder/_19_  (.D(\u_decoder/_00_ ),
    .CLK(clknet_3_2__leaf_clk),
    .Q(dec_data_bit));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 \u_decoder/_20_  (.D(\u_decoder/_02_ ),
    .CLK(clknet_3_2__leaf_clk),
    .Q(dec_data_valid));
 gf180mcu_fd_sc_mcu9t5v0__nand2_4 \u_destuffer/_22_  (.A1(\u_destuffer/ones [2]),
    .A2(\u_destuffer/ones [1]),
    .ZN(\u_destuffer/_06_ ));
 gf180mcu_fd_sc_mcu9t5v0__inv_3 \u_destuffer/_23_  (.I(sync_next),
    .ZN(\u_destuffer/_07_ ));
 gf180mcu_fd_sc_mcu9t5v0__nand4_4 \u_destuffer/_24_  (.A1(dec_data_bit),
    .A2(destuff_in_valid),
    .A3(\u_destuffer/_07_ ),
    .A4(int_rst_n),
    .ZN(\u_destuffer/_08_ ));
 gf180mcu_fd_sc_mcu9t5v0__nor3_1 \u_destuffer/_25_  (.A1(\u_destuffer/ones [0]),
    .A2(\u_destuffer/_06_ ),
    .A3(\u_destuffer/_08_ ),
    .ZN(\u_destuffer/_00_ ));
 gf180mcu_fd_sc_mcu9t5v0__nand2_2 \u_destuffer/_26_  (.A1(\u_destuffer/_07_ ),
    .A2(int_rst_n),
    .ZN(\u_destuffer/_09_ ));
 gf180mcu_fd_sc_mcu9t5v0__inv_4 \u_destuffer/_27_  (.I(destuff_in_valid),
    .ZN(\u_destuffer/_10_ ));
 gf180mcu_fd_sc_mcu9t5v0__aoi21_4 \u_destuffer/_28_  (.A1(dec_data_bit),
    .A2(\u_destuffer/_06_ ),
    .B(\u_destuffer/_10_ ),
    .ZN(\u_destuffer/_11_ ));
 gf180mcu_fd_sc_mcu9t5v0__xnor2_1 \u_destuffer/_29_  (.A1(destuff_in_valid),
    .A2(\u_destuffer/ones [0]),
    .ZN(\u_destuffer/_12_ ));
 gf180mcu_fd_sc_mcu9t5v0__nor3_2 \u_destuffer/_30_  (.A1(\u_destuffer/_09_ ),
    .A2(\u_destuffer/_11_ ),
    .A3(\u_destuffer/_12_ ),
    .ZN(\u_destuffer/_01_ ));
 gf180mcu_fd_sc_mcu9t5v0__nand2_4 \u_destuffer/_31_  (.A1(destuff_in_valid),
    .A2(\u_destuffer/ones [0]),
    .ZN(\u_destuffer/_13_ ));
 gf180mcu_fd_sc_mcu9t5v0__xor2_2 \u_destuffer/_32_  (.A1(\u_destuffer/ones [1]),
    .A2(\u_destuffer/_13_ ),
    .Z(\u_destuffer/_14_ ));
 gf180mcu_fd_sc_mcu9t5v0__nor3_2 \u_destuffer/_33_  (.A1(\u_destuffer/_09_ ),
    .A2(\u_destuffer/_11_ ),
    .A3(\u_destuffer/_14_ ),
    .ZN(\u_destuffer/_02_ ));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_1 \u_destuffer/_34_  (.I(\u_destuffer/ones [2]),
    .ZN(\u_destuffer/_15_ ));
 gf180mcu_fd_sc_mcu9t5v0__nand3_1 \u_destuffer/_35_  (.A1(destuff_in_valid),
    .A2(\u_destuffer/ones [1]),
    .A3(\u_destuffer/ones [0]),
    .ZN(\u_destuffer/_16_ ));
 gf180mcu_fd_sc_mcu9t5v0__aoi211_2 \u_destuffer/_36_  (.A1(\u_destuffer/_15_ ),
    .A2(\u_destuffer/_16_ ),
    .B(\u_destuffer/_11_ ),
    .C(\u_destuffer/_09_ ),
    .ZN(\u_destuffer/_03_ ));
 gf180mcu_fd_sc_mcu9t5v0__nor2_2 \u_destuffer/_37_  (.A1(\u_destuffer/ones [0]),
    .A2(\u_destuffer/_06_ ),
    .ZN(\u_destuffer/_17_ ));
 gf180mcu_fd_sc_mcu9t5v0__nor3_1 \u_destuffer/_38_  (.A1(\u_destuffer/_10_ ),
    .A2(\u_destuffer/_17_ ),
    .A3(\u_destuffer/_09_ ),
    .ZN(\u_destuffer/_04_ ));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_1 \u_destuffer/_39_  (.I(destuff_out_bit),
    .ZN(\u_destuffer/_18_ ));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_2 \u_destuffer/_40_  (.I(\u_destuffer/ones [0]),
    .ZN(\u_destuffer/_19_ ));
 gf180mcu_fd_sc_mcu9t5v0__and2_4 \u_destuffer/_41_  (.A1(\u_destuffer/ones [2]),
    .A2(\u_destuffer/ones [1]),
    .Z(\u_destuffer/_20_ ));
 gf180mcu_fd_sc_mcu9t5v0__aoi21_4 \u_destuffer/_42_  (.A1(\u_destuffer/_19_ ),
    .A2(\u_destuffer/_20_ ),
    .B(\u_destuffer/_10_ ),
    .ZN(\u_destuffer/_21_ ));
 gf180mcu_fd_sc_mcu9t5v0__oai32_4 \u_destuffer/_43_  (.A1(\u_destuffer/_18_ ),
    .A2(\u_destuffer/_09_ ),
    .A3(\u_destuffer/_21_ ),
    .B1(\u_destuffer/_08_ ),
    .B2(\u_destuffer/_17_ ),
    .ZN(\u_destuffer/_05_ ));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 \u_destuffer/_44_  (.D(\u_destuffer/_00_ ),
    .CLK(clknet_3_0__leaf_clk),
    .Q(destuff_stuff_err));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 \u_destuffer/_45_  (.D(\u_destuffer/_01_ ),
    .CLK(clknet_3_2__leaf_clk),
    .Q(\u_destuffer/ones [0]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 \u_destuffer/_46_  (.D(\u_destuffer/_02_ ),
    .CLK(clknet_3_2__leaf_clk),
    .Q(\u_destuffer/ones [1]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 \u_destuffer/_47_  (.D(\u_destuffer/_03_ ),
    .CLK(clknet_3_0__leaf_clk),
    .Q(\u_destuffer/ones [2]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 \u_destuffer/_48_  (.D(\u_destuffer/_05_ ),
    .CLK(clknet_3_0__leaf_clk),
    .Q(destuff_out_bit));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 \u_destuffer/_49_  (.D(\u_destuffer/_04_ ),
    .CLK(clknet_3_0__leaf_clk),
    .Q(destuff_out_valid));
 gf180mcu_fd_sc_mcu9t5v0__inv_2 \u_encoder/_07_  (.I(stuff_out_valid),
    .ZN(\u_encoder/_05_ ));
 gf180mcu_fd_sc_mcu9t5v0__oai21_1 \u_encoder/_08_  (.A1(\u_encoder/_05_ ),
    .A2(stuff_out_bit),
    .B(enc_line_bit),
    .ZN(\u_encoder/_06_ ));
 gf180mcu_fd_sc_mcu9t5v0__or3_4 \u_encoder/_09_  (.A1(enc_line_bit),
    .A2(\u_encoder/_05_ ),
    .A3(stuff_out_bit),
    .Z(\u_encoder/_02_ ));
 gf180mcu_fd_sc_mcu9t5v0__inv_1 \u_encoder/_10_  (.I(int_rst_n),
    .ZN(\u_encoder/_03_ ));
 gf180mcu_fd_sc_mcu9t5v0__nor2_1 \u_encoder/_11_  (.A1(tx_state[5]),
    .A2(\u_encoder/_03_ ),
    .ZN(\u_encoder/_04_ ));
 gf180mcu_fd_sc_mcu9t5v0__nand3_2 \u_encoder/_12_  (.A1(\u_encoder/_06_ ),
    .A2(\u_encoder/_02_ ),
    .A3(\u_encoder/_04_ ),
    .ZN(\u_encoder/_00_ ));
 gf180mcu_fd_sc_mcu9t5v0__nor3_1 \u_encoder/_13_  (.A1(\u_encoder/_05_ ),
    .A2(tx_state[5]),
    .A3(\u_encoder/_03_ ),
    .ZN(\u_encoder/_01_ ));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 \u_encoder/_14_  (.D(\u_encoder/_00_ ),
    .CLK(clknet_3_6__leaf_clk),
    .Q(enc_line_bit));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 \u_encoder/_15_  (.D(\u_encoder/_01_ ),
    .CLK(clknet_3_6__leaf_clk),
    .Q(enc_line_valid));
 gf180mcu_fd_sc_mcu9t5v0__nor2_1 \u_eop_detector/_27_  (.A1(line_state[0]),
    .A2(line_state[1]),
    .ZN(\u_eop_detector/_08_ ));
 gf180mcu_fd_sc_mcu9t5v0__nand2_1 \u_eop_detector/_28_  (.A1(int_rst_n),
    .A2(\u_eop_detector/_08_ ),
    .ZN(\u_eop_detector/_09_ ));
 gf180mcu_fd_sc_mcu9t5v0__and3_4 \u_eop_detector/_29_  (.A1(\u_eop_detector/se0_count [3]),
    .A2(\u_eop_detector/se0_count [4]),
    .A3(\u_eop_detector/se0_count [2]),
    .Z(\u_eop_detector/_10_ ));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_1 \u_eop_detector/_30_  (.I(\u_eop_detector/se0_count [0]),
    .ZN(\u_eop_detector/_11_ ));
 gf180mcu_fd_sc_mcu9t5v0__nor3_1 \u_eop_detector/_31_  (.A1(\u_eop_detector/se0_count [5]),
    .A2(\u_eop_detector/_11_ ),
    .A3(\u_eop_detector/se0_count [1]),
    .ZN(\u_eop_detector/_12_ ));
 gf180mcu_fd_sc_mcu9t5v0__aoi21_1 \u_eop_detector/_32_  (.A1(\u_eop_detector/_10_ ),
    .A2(\u_eop_detector/_12_ ),
    .B(bus_reset),
    .ZN(\u_eop_detector/_13_ ));
 gf180mcu_fd_sc_mcu9t5v0__nor2_1 \u_eop_detector/_33_  (.A1(\u_eop_detector/_09_ ),
    .A2(\u_eop_detector/_13_ ),
    .ZN(\u_eop_detector/_00_ ));
 gf180mcu_fd_sc_mcu9t5v0__inv_1 \u_eop_detector/_34_  (.I(\u_eop_detector/se0_count [1]),
    .ZN(\u_eop_detector/_14_ ));
 gf180mcu_fd_sc_mcu9t5v0__nor4_4 \u_eop_detector/_35_  (.A1(\u_eop_detector/se0_count [5]),
    .A2(\u_eop_detector/_11_ ),
    .A3(\u_eop_detector/_14_ ),
    .A4(\u_eop_detector/_10_ ),
    .ZN(\u_eop_detector/_15_ ));
 gf180mcu_fd_sc_mcu9t5v0__xnor2_1 \u_eop_detector/_36_  (.A1(\u_eop_detector/se0_count [2]),
    .A2(\u_eop_detector/_15_ ),
    .ZN(\u_eop_detector/_16_ ));
 gf180mcu_fd_sc_mcu9t5v0__nor2_2 \u_eop_detector/_37_  (.A1(\u_eop_detector/_09_ ),
    .A2(\u_eop_detector/_16_ ),
    .ZN(\u_eop_detector/_01_ ));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_1 \u_eop_detector/_38_  (.I(\u_eop_detector/se0_count [5]),
    .ZN(\u_eop_detector/_17_ ));
 gf180mcu_fd_sc_mcu9t5v0__nand2_1 \u_eop_detector/_39_  (.A1(\u_eop_detector/_17_ ),
    .A2(\u_eop_detector/se0_count [0]),
    .ZN(\u_eop_detector/_18_ ));
 gf180mcu_fd_sc_mcu9t5v0__aoi211_1 \u_eop_detector/_40_  (.A1(\u_eop_detector/_14_ ),
    .A2(\u_eop_detector/_18_ ),
    .B(\u_eop_detector/_15_ ),
    .C(\u_eop_detector/_09_ ),
    .ZN(\u_eop_detector/_02_ ));
 gf180mcu_fd_sc_mcu9t5v0__aoi21_1 \u_eop_detector/_41_  (.A1(\u_eop_detector/se0_count [1]),
    .A2(\u_eop_detector/_10_ ),
    .B(\u_eop_detector/_18_ ),
    .ZN(\u_eop_detector/_19_ ));
 gf180mcu_fd_sc_mcu9t5v0__nand2_1 \u_eop_detector/_42_  (.A1(\u_eop_detector/se0_count [1]),
    .A2(\u_eop_detector/_10_ ),
    .ZN(\u_eop_detector/_20_ ));
 gf180mcu_fd_sc_mcu9t5v0__aoi21_1 \u_eop_detector/_43_  (.A1(\u_eop_detector/_17_ ),
    .A2(\u_eop_detector/_20_ ),
    .B(\u_eop_detector/se0_count [0]),
    .ZN(\u_eop_detector/_21_ ));
 gf180mcu_fd_sc_mcu9t5v0__nor3_1 \u_eop_detector/_44_  (.A1(\u_eop_detector/_09_ ),
    .A2(\u_eop_detector/_19_ ),
    .A3(\u_eop_detector/_21_ ),
    .ZN(\u_eop_detector/_03_ ));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_1 \u_eop_detector/_45_  (.I(\u_eop_detector/se0_count [4]),
    .ZN(\u_eop_detector/_22_ ));
 gf180mcu_fd_sc_mcu9t5v0__nand3_1 \u_eop_detector/_46_  (.A1(\u_eop_detector/se0_count [3]),
    .A2(\u_eop_detector/se0_count [2]),
    .A3(\u_eop_detector/_15_ ),
    .ZN(\u_eop_detector/_23_ ));
 gf180mcu_fd_sc_mcu9t5v0__aoi21_1 \u_eop_detector/_47_  (.A1(\u_eop_detector/_22_ ),
    .A2(\u_eop_detector/_23_ ),
    .B(\u_eop_detector/_09_ ),
    .ZN(\u_eop_detector/_04_ ));
 gf180mcu_fd_sc_mcu9t5v0__and3_1 \u_eop_detector/_48_  (.A1(\u_eop_detector/se0_count [3]),
    .A2(\u_eop_detector/se0_count [2]),
    .A3(\u_eop_detector/_15_ ),
    .Z(\u_eop_detector/_24_ ));
 gf180mcu_fd_sc_mcu9t5v0__aoi21_1 \u_eop_detector/_49_  (.A1(\u_eop_detector/se0_count [2]),
    .A2(\u_eop_detector/_15_ ),
    .B(\u_eop_detector/se0_count [3]),
    .ZN(\u_eop_detector/_25_ ));
 gf180mcu_fd_sc_mcu9t5v0__nor3_1 \u_eop_detector/_50_  (.A1(\u_eop_detector/_09_ ),
    .A2(\u_eop_detector/_24_ ),
    .A3(\u_eop_detector/_25_ ),
    .ZN(\u_eop_detector/_05_ ));
 gf180mcu_fd_sc_mcu9t5v0__nor2_1 \u_eop_detector/_51_  (.A1(\u_eop_detector/_17_ ),
    .A2(\u_eop_detector/_09_ ),
    .ZN(\u_eop_detector/_06_ ));
 gf180mcu_fd_sc_mcu9t5v0__nor4_1 \u_eop_detector/_52_  (.A1(\u_eop_detector/se0_count [3]),
    .A2(\u_eop_detector/se0_count [4]),
    .A3(\u_eop_detector/se0_count [2]),
    .A4(\u_eop_detector/_09_ ),
    .ZN(\u_eop_detector/_26_ ));
 gf180mcu_fd_sc_mcu9t5v0__and2_1 \u_eop_detector/_53_  (.A1(\u_eop_detector/_12_ ),
    .A2(\u_eop_detector/_26_ ),
    .Z(\u_eop_detector/_07_ ));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 \u_eop_detector/_54_  (.D(\u_eop_detector/_00_ ),
    .CLK(clknet_3_3__leaf_clk),
    .Q(bus_reset));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 \u_eop_detector/_55_  (.D(\u_eop_detector/_07_ ),
    .CLK(clknet_3_3__leaf_clk),
    .Q(eop_pulse));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 \u_eop_detector/_56_  (.D(\u_eop_detector/_03_ ),
    .CLK(clknet_3_3__leaf_clk),
    .Q(\u_eop_detector/se0_count [0]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 \u_eop_detector/_57_  (.D(\u_eop_detector/_02_ ),
    .CLK(clknet_3_3__leaf_clk),
    .Q(\u_eop_detector/se0_count [1]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 \u_eop_detector/_58_  (.D(\u_eop_detector/_01_ ),
    .CLK(clknet_3_2__leaf_clk),
    .Q(\u_eop_detector/se0_count [2]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 \u_eop_detector/_59_  (.D(\u_eop_detector/_05_ ),
    .CLK(clknet_3_2__leaf_clk),
    .Q(\u_eop_detector/se0_count [3]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 \u_eop_detector/_60_  (.D(\u_eop_detector/_04_ ),
    .CLK(clknet_3_2__leaf_clk),
    .Q(\u_eop_detector/se0_count [4]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 \u_eop_detector/_61_  (.D(\u_eop_detector/_06_ ),
    .CLK(clknet_3_3__leaf_clk),
    .Q(\u_eop_detector/se0_count [5]));
 gf180mcu_fd_sc_mcu9t5v0__inv_2 \u_line_state/_3_  (.I(rxdp),
    .ZN(\u_line_state/_2_ ));
 gf180mcu_fd_sc_mcu9t5v0__nand2_1 \u_line_state/_4_  (.A1(\u_line_state/_2_ ),
    .A2(int_rst_n),
    .ZN(\u_line_state/_0_ ));
 gf180mcu_fd_sc_mcu9t5v0__and2_4 \u_line_state/_5_  (.A1(int_rst_n),
    .A2(rxdm),
    .Z(\u_line_state/_1_ ));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 \u_line_state/_6_  (.D(\u_line_state/_0_ ),
    .CLK(clknet_3_1__leaf_clk),
    .Q(line_state[0]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 \u_line_state/_7_  (.D(\u_line_state/_1_ ),
    .CLK(clknet_3_4__leaf_clk),
    .Q(line_state[1]));
 gf180mcu_fd_sc_mcu9t5v0__nand2_4 \u_stuffer/_19_  (.A1(\u_stuffer/ones [2]),
    .A2(\u_stuffer/ones [1]),
    .ZN(\u_stuffer/_06_ ));
 gf180mcu_fd_sc_mcu9t5v0__or2_2 \u_stuffer/_20_  (.A1(\u_stuffer/ones [0]),
    .A2(\u_stuffer/_06_ ),
    .Z(stuff_in_ready));
 gf180mcu_fd_sc_mcu9t5v0__nand2_1 \u_stuffer/_21_  (.A1(stuffer_in_bit),
    .A2(\u_stuffer/_06_ ),
    .ZN(\u_stuffer/_07_ ));
 gf180mcu_fd_sc_mcu9t5v0__nand2_4 \u_stuffer/_22_  (.A1(stuffer_in_valid),
    .A2(\u_stuffer/ones [0]),
    .ZN(\u_stuffer/_08_ ));
 gf180mcu_fd_sc_mcu9t5v0__xor2_2 \u_stuffer/_23_  (.A1(\u_stuffer/ones [1]),
    .A2(\u_stuffer/_08_ ),
    .Z(\u_stuffer/_09_ ));
 gf180mcu_fd_sc_mcu9t5v0__inv_2 \u_stuffer/_24_  (.I(tx_state[5]),
    .ZN(\u_stuffer/_10_ ));
 gf180mcu_fd_sc_mcu9t5v0__nand2_2 \u_stuffer/_25_  (.A1(\u_stuffer/_10_ ),
    .A2(int_rst_n),
    .ZN(\u_stuffer/_11_ ));
 gf180mcu_fd_sc_mcu9t5v0__aoi211_2 \u_stuffer/_26_  (.A1(stuffer_in_valid),
    .A2(\u_stuffer/_07_ ),
    .B(\u_stuffer/_09_ ),
    .C(\u_stuffer/_11_ ),
    .ZN(\u_stuffer/_00_ ));
 gf180mcu_fd_sc_mcu9t5v0__nand3_1 \u_stuffer/_27_  (.A1(stuffer_in_valid),
    .A2(\u_stuffer/ones [0]),
    .A3(\u_stuffer/ones [1]),
    .ZN(\u_stuffer/_12_ ));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_1 \u_stuffer/_28_  (.I(\u_stuffer/ones [2]),
    .ZN(\u_stuffer/_13_ ));
 gf180mcu_fd_sc_mcu9t5v0__aoi221_1 \u_stuffer/_29_  (.A1(stuffer_in_valid),
    .A2(\u_stuffer/_07_ ),
    .B1(\u_stuffer/_12_ ),
    .B2(\u_stuffer/_13_ ),
    .C(\u_stuffer/_11_ ),
    .ZN(\u_stuffer/_01_ ));
 gf180mcu_fd_sc_mcu9t5v0__oai211_2 \u_stuffer/_30_  (.A1(\u_stuffer/ones [0]),
    .A2(\u_stuffer/_06_ ),
    .B(int_rst_n),
    .C(\u_stuffer/_10_ ),
    .ZN(\u_stuffer/_14_ ));
 gf180mcu_fd_sc_mcu9t5v0__aoi21_1 \u_stuffer/_31_  (.A1(stuffer_in_valid),
    .A2(stuffer_in_bit),
    .B(\u_stuffer/ones [0]),
    .ZN(\u_stuffer/_15_ ));
 gf180mcu_fd_sc_mcu9t5v0__aoi211_1 \u_stuffer/_32_  (.A1(stuffer_in_valid),
    .A2(\u_stuffer/ones [0]),
    .B(\u_stuffer/_14_ ),
    .C(\u_stuffer/_15_ ),
    .ZN(\u_stuffer/_02_ ));
 gf180mcu_fd_sc_mcu9t5v0__nand2_1 \u_stuffer/_33_  (.A1(stuffer_in_valid),
    .A2(stuffer_in_bit),
    .ZN(\u_stuffer/_16_ ));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_1 \u_stuffer/_34_  (.I(stuffer_in_valid),
    .ZN(\u_stuffer/_17_ ));
 gf180mcu_fd_sc_mcu9t5v0__nand2_1 \u_stuffer/_35_  (.A1(stuff_out_bit),
    .A2(\u_stuffer/_17_ ),
    .ZN(\u_stuffer/_18_ ));
 gf180mcu_fd_sc_mcu9t5v0__oai22_1 \u_stuffer/_36_  (.A1(\u_stuffer/_14_ ),
    .A2(\u_stuffer/_16_ ),
    .B1(\u_stuffer/_18_ ),
    .B2(\u_stuffer/_11_ ),
    .ZN(\u_stuffer/_03_ ));
 gf180mcu_fd_sc_mcu9t5v0__nor3_2 \u_stuffer/_37_  (.A1(\u_stuffer/_17_ ),
    .A2(stuff_in_ready),
    .A3(\u_stuffer/_11_ ),
    .ZN(\u_stuffer/_04_ ));
 gf180mcu_fd_sc_mcu9t5v0__nor2_1 \u_stuffer/_38_  (.A1(\u_stuffer/_17_ ),
    .A2(\u_stuffer/_11_ ),
    .ZN(\u_stuffer/_05_ ));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 \u_stuffer/_39_  (.D(\u_stuffer/_02_ ),
    .CLK(clknet_3_7__leaf_clk),
    .Q(\u_stuffer/ones [0]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 \u_stuffer/_40_  (.D(\u_stuffer/_00_ ),
    .CLK(clknet_3_7__leaf_clk),
    .Q(\u_stuffer/ones [1]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 \u_stuffer/_41_  (.D(\u_stuffer/_01_ ),
    .CLK(clknet_3_7__leaf_clk),
    .Q(\u_stuffer/ones [2]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 \u_stuffer/_42_  (.D(\u_stuffer/_04_ ),
    .CLK(clknet_3_7__leaf_clk),
    .Q(\u_stuffer/out_stuffed ));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 \u_stuffer/_43_  (.D(\u_stuffer/_03_ ),
    .CLK(clknet_3_7__leaf_clk),
    .Q(stuff_out_bit));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 \u_stuffer/_44_  (.D(\u_stuffer/_05_ ),
    .CLK(clknet_3_6__leaf_clk),
    .Q(stuff_out_valid));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_1 \u_sync_detector/_16_  (.I(_009_),
    .ZN(\u_sync_detector/_05_ ));
 gf180mcu_fd_sc_mcu9t5v0__nand3_4 \u_sync_detector/_17_  (.A1(\u_sync_detector/match [0]),
    .A2(\u_sync_detector/match [1]),
    .A3(\u_sync_detector/match [2]),
    .ZN(\u_sync_detector/_06_ ));
 gf180mcu_fd_sc_mcu9t5v0__nand2_4 \u_sync_detector/_18_  (.A1(dec_data_valid),
    .A2(dec_data_bit),
    .ZN(\u_sync_detector/_07_ ));
 gf180mcu_fd_sc_mcu9t5v0__nor4_4 \u_sync_detector/_19_  (.A1(\u_sync_detector/match [3]),
    .A2(\u_sync_detector/_05_ ),
    .A3(\u_sync_detector/_06_ ),
    .A4(\u_sync_detector/_07_ ),
    .ZN(sync_next));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_1 \u_sync_detector/_20_  (.I(\u_sync_detector/match [3]),
    .ZN(\u_sync_detector/_08_ ));
 gf180mcu_fd_sc_mcu9t5v0__nand3_4 \u_sync_detector/_21_  (.A1(_009_),
    .A2(int_rst_n),
    .A3(\u_sync_detector/_07_ ),
    .ZN(\u_sync_detector/_09_ ));
 gf180mcu_fd_sc_mcu9t5v0__and3_2 \u_sync_detector/_22_  (.A1(\u_sync_detector/match [0]),
    .A2(dec_data_valid),
    .A3(\u_sync_detector/match [1]),
    .Z(\u_sync_detector/_10_ ));
 gf180mcu_fd_sc_mcu9t5v0__and2_2 \u_sync_detector/_23_  (.A1(\u_sync_detector/match [2]),
    .A2(\u_sync_detector/_10_ ),
    .Z(\u_sync_detector/_11_ ));
 gf180mcu_fd_sc_mcu9t5v0__nor3_2 \u_sync_detector/_24_  (.A1(\u_sync_detector/_08_ ),
    .A2(\u_sync_detector/_09_ ),
    .A3(\u_sync_detector/_11_ ),
    .ZN(\u_sync_detector/_00_ ));
 gf180mcu_fd_sc_mcu9t5v0__nor2_1 \u_sync_detector/_25_  (.A1(\u_sync_detector/match [2]),
    .A2(\u_sync_detector/_10_ ),
    .ZN(\u_sync_detector/_12_ ));
 gf180mcu_fd_sc_mcu9t5v0__nor3_2 \u_sync_detector/_26_  (.A1(\u_sync_detector/_09_ ),
    .A2(\u_sync_detector/_11_ ),
    .A3(\u_sync_detector/_12_ ),
    .ZN(\u_sync_detector/_01_ ));
 gf180mcu_fd_sc_mcu9t5v0__and2_1 \u_sync_detector/_27_  (.A1(\u_sync_detector/match [0]),
    .A2(dec_data_valid),
    .Z(\u_sync_detector/_13_ ));
 gf180mcu_fd_sc_mcu9t5v0__nor2_1 \u_sync_detector/_28_  (.A1(\u_sync_detector/match [1]),
    .A2(\u_sync_detector/_13_ ),
    .ZN(\u_sync_detector/_14_ ));
 gf180mcu_fd_sc_mcu9t5v0__nor3_1 \u_sync_detector/_29_  (.A1(\u_sync_detector/_09_ ),
    .A2(\u_sync_detector/_10_ ),
    .A3(\u_sync_detector/_14_ ),
    .ZN(\u_sync_detector/_02_ ));
 gf180mcu_fd_sc_mcu9t5v0__nor2_1 \u_sync_detector/_30_  (.A1(\u_sync_detector/match [0]),
    .A2(dec_data_valid),
    .ZN(\u_sync_detector/_15_ ));
 gf180mcu_fd_sc_mcu9t5v0__aoi211_1 \u_sync_detector/_31_  (.A1(\u_sync_detector/_06_ ),
    .A2(\u_sync_detector/_13_ ),
    .B(\u_sync_detector/_15_ ),
    .C(\u_sync_detector/_09_ ),
    .ZN(\u_sync_detector/_03_ ));
 gf180mcu_fd_sc_mcu9t5v0__and2_2 \u_sync_detector/_32_  (.A1(int_rst_n),
    .A2(sync_next),
    .Z(\u_sync_detector/_04_ ));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 \u_sync_detector/_33_  (.D(\u_sync_detector/_04_ ),
    .CLK(clknet_3_3__leaf_clk),
    .Q(\u_sync_detector/sync_valid ));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 \u_sync_detector/_34_  (.D(\u_sync_detector/_03_ ),
    .CLK(clknet_3_2__leaf_clk),
    .Q(\u_sync_detector/match [0]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 \u_sync_detector/_35_  (.D(\u_sync_detector/_02_ ),
    .CLK(clknet_3_2__leaf_clk),
    .Q(\u_sync_detector/match [1]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 \u_sync_detector/_36_  (.D(\u_sync_detector/_01_ ),
    .CLK(clknet_3_2__leaf_clk),
    .Q(\u_sync_detector/match [2]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 \u_sync_detector/_37_  (.D(\u_sync_detector/_00_ ),
    .CLK(clknet_3_2__leaf_clk),
    .Q(\u_sync_detector/match [3]));
 assign LineState[0] = line_state[0];
 assign LineState[1] = line_state[1];
 assign RxActive = rx_receiving;
endmodule
