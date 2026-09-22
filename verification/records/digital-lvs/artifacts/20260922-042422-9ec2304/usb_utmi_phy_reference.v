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
 wire clknet_3_3__leaf_clk;
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
 wire clknet_0_clk;
 wire _055_;
 wire _056_;
 wire _057_;
 wire _058_;
 wire _059_;
 wire _060_;
 wire _061_;
 wire _062_;
 wire _063_;
 wire _064_;
 wire clknet_3_0__leaf_clk;
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
 wire _079_;
 wire _080_;
 wire _081_;
 wire _082_;
 wire _083_;
 wire _084_;
 wire _085_;
 wire _086_;
 wire clknet_3_1__leaf_clk;
 wire _088_;
 wire _089_;
 wire _090_;
 wire _091_;
 wire _092_;
 wire clknet_3_4__leaf_clk;
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
 wire _112_;
 wire _113_;
 wire _114_;
 wire _115_;
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
 wire _146_;
 wire _147_;
 wire bus_reset;
 wire dec_bit_level;
 wire dec_bit_strobe;
 wire dec_data_bit;
 wire dec_data_strobe;
 wire entering_sync;
 wire eop_pulse;
 wire first_byte;
 wire clknet_3_2__leaf_clk;
 wire nrzi_level;
 wire raw_mode;
 wire rx_assembly_en;
 wire rx_bit_valid;
 wire rx_out_bit;
 wire rx_receiving;
 wire rx_stuff_err;
 wire stuff_bit_out;
 wire stuff_consume;
 wire stuff_pending_after;
 wire sync_next;
 wire tx_body_active;
 wire \u_decoder/_00_ ;
 wire \u_decoder/_01_ ;
 wire \u_decoder/_02_ ;
 wire \u_decoder/_03_ ;
 wire \u_decoder/_04_ ;
 wire \u_decoder/prev_level ;
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
 wire \u_encoder/_0_ ;
 wire \u_encoder/_1_ ;
 wire \u_encoder/_2_ ;
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
 wire [2:0] byte_idx;
 wire [7:0] byte_reg;
 wire [1:0] line_state;
 wire [2:0] rx_bitcnt;
 wire [7:0] rx_shift;
 wire [2:0] sync_idx;
 wire [7:0] tx_state;
 wire [2:0] \u_destuffer/ones_run ;
 wire [5:0] \u_eop_detector/se0_count ;
 wire [2:0] \u_stuffer/run ;
 wire [3:0] \u_sync_detector/match ;

 gf180mcu_fd_sc_mcu9t5v0__clkinv_1 _148_ (.I(rx_receiving),
    .ZN(_010_));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_1 _149_ (.I(Reset),
    .ZN(_051_));
 gf180mcu_fd_sc_mcu9t5v0__nand2_2 _150_ (.A1(rst_n),
    .A2(_051_),
    .ZN(_052_));
 gf180mcu_fd_sc_mcu9t5v0__inv_2 _151_ (.I(_052_),
    .ZN(_053_));
 gf180mcu_fd_sc_mcu9t5v0__nand4_4 _154_ (.A1(byte_idx[0]),
    .A2(byte_idx[1]),
    .A3(byte_idx[2]),
    .A4(tx_state[2]),
    .ZN(_055_));
 gf180mcu_fd_sc_mcu9t5v0__or2_1 _155_ (.A1(TxValid),
    .A2(_055_),
    .Z(_056_));
 gf180mcu_fd_sc_mcu9t5v0__nand2_1 _156_ (.A1(stuff_consume),
    .A2(_053_),
    .ZN(_057_));
 gf180mcu_fd_sc_mcu9t5v0__nand2_1 _157_ (.A1(tx_state[6]),
    .A2(_053_),
    .ZN(_058_));
 gf180mcu_fd_sc_mcu9t5v0__oai31_1 _158_ (.A1(stuff_pending_after),
    .A2(_056_),
    .A3(_057_),
    .B(_058_),
    .ZN(_005_));
 gf180mcu_fd_sc_mcu9t5v0__and2_1 _159_ (.A1(tx_state[1]),
    .A2(_053_),
    .Z(_001_));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_1 _160_ (.I(tx_state[0]),
    .ZN(_059_));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_1 _161_ (.I(tx_state[7]),
    .ZN(_060_));
 gf180mcu_fd_sc_mcu9t5v0__oai211_1 _162_ (.A1(TxValid),
    .A2(_059_),
    .B(_060_),
    .C(_053_),
    .ZN(_004_));
 gf180mcu_fd_sc_mcu9t5v0__nand2_2 _163_ (.A1(TxValid),
    .A2(tx_state[0]),
    .ZN(_061_));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_1 _164_ (.I(_061_),
    .ZN(entering_sync));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_1 _165_ (.I(tx_state[4]),
    .ZN(_062_));
 gf180mcu_fd_sc_mcu9t5v0__and3_1 _166_ (.A1(sync_idx[0]),
    .A2(sync_idx[2]),
    .A3(sync_idx[1]),
    .Z(_063_));
 gf180mcu_fd_sc_mcu9t5v0__or2_1 _167_ (.A1(_062_),
    .A2(_063_),
    .Z(_064_));
 gf180mcu_fd_sc_mcu9t5v0__aoi21_1 _169_ (.A1(_061_),
    .A2(_064_),
    .B(_052_),
    .ZN(_007_));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_1 _170_ (.I(stuff_pending_after),
    .ZN(_066_));
 gf180mcu_fd_sc_mcu9t5v0__nor3_1 _171_ (.A1(_066_),
    .A2(_056_),
    .A3(_057_),
    .ZN(_002_));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_1 _172_ (.I(line_state[0]),
    .ZN(_067_));
 gf180mcu_fd_sc_mcu9t5v0__nor2_1 _173_ (.A1(_067_),
    .A2(line_state[1]),
    .ZN(dec_bit_level));
 gf180mcu_fd_sc_mcu9t5v0__xor2_1 _174_ (.A1(line_state[0]),
    .A2(line_state[1]),
    .Z(dec_bit_strobe));
 gf180mcu_fd_sc_mcu9t5v0__nor2_1 _175_ (.A1(tx_state[2]),
    .A2(tx_state[6]),
    .ZN(_068_));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_1 _176_ (.I(_068_),
    .ZN(tx_body_active));
 gf180mcu_fd_sc_mcu9t5v0__nor4_1 _177_ (.A1(tx_state[2]),
    .A2(tx_state[6]),
    .A3(tx_state[4]),
    .A4(tx_state[1]),
    .ZN(_069_));
 gf180mcu_fd_sc_mcu9t5v0__or2_1 _178_ (.A1(tx_state[5]),
    .A2(tx_state[3]),
    .Z(_070_));
 gf180mcu_fd_sc_mcu9t5v0__nor4_1 _179_ (.A1(tx_state[7]),
    .A2(nrzi_level),
    .A3(_069_),
    .A4(_070_),
    .ZN(txdm));
 gf180mcu_fd_sc_mcu9t5v0__nor3_1 _180_ (.A1(tx_state[7]),
    .A2(nrzi_level),
    .A3(_069_),
    .ZN(_071_));
 gf180mcu_fd_sc_mcu9t5v0__nor2_1 _181_ (.A1(_071_),
    .A2(_070_),
    .ZN(txdp));
 gf180mcu_fd_sc_mcu9t5v0__and2_1 _182_ (.A1(tx_state[5]),
    .A2(_053_),
    .Z(_000_));
 gf180mcu_fd_sc_mcu9t5v0__and2_1 _183_ (.A1(tx_state[3]),
    .A2(_053_),
    .Z(_003_));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_1 _184_ (.I(stuff_consume),
    .ZN(_072_));
 gf180mcu_fd_sc_mcu9t5v0__oai21_1 _185_ (.A1(_072_),
    .A2(_055_),
    .B(_059_),
    .ZN(TxReady));
 gf180mcu_fd_sc_mcu9t5v0__nand2_1 _186_ (.A1(tx_state[4]),
    .A2(_063_),
    .ZN(_073_));
 gf180mcu_fd_sc_mcu9t5v0__nand4_4 _187_ (.A1(byte_idx[0]),
    .A2(byte_idx[1]),
    .A3(byte_idx[2]),
    .A4(stuff_consume),
    .ZN(_074_));
 gf180mcu_fd_sc_mcu9t5v0__oai21_1 _188_ (.A1(TxValid),
    .A2(_074_),
    .B(tx_state[2]),
    .ZN(_075_));
 gf180mcu_fd_sc_mcu9t5v0__aoi21_1 _189_ (.A1(_073_),
    .A2(_075_),
    .B(_052_),
    .ZN(_006_));
 gf180mcu_fd_sc_mcu9t5v0__nor2_1 _190_ (.A1(tx_state[4]),
    .A2(entering_sync),
    .ZN(_076_));
 gf180mcu_fd_sc_mcu9t5v0__mux2_1 _191_ (.I0(_063_),
    .I1(stuff_bit_out),
    .S(_076_),
    .Z(_013_));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_1 _192_ (.I(OpMode[1]),
    .ZN(_077_));
 gf180mcu_fd_sc_mcu9t5v0__nor2_1 _193_ (.A1(_077_),
    .A2(OpMode[0]),
    .ZN(raw_mode));
 gf180mcu_fd_sc_mcu9t5v0__nor3_1 _194_ (.A1(_077_),
    .A2(OpMode[0]),
    .A3(_068_),
    .ZN(_009_));
 gf180mcu_fd_sc_mcu9t5v0__nand2_1 _195_ (.A1(_068_),
    .A2(_076_),
    .ZN(_011_));
 gf180mcu_fd_sc_mcu9t5v0__mux4_1 _196_ (.I0(byte_reg[2]),
    .I1(byte_reg[3]),
    .I2(byte_reg[6]),
    .I3(byte_reg[7]),
    .S0(byte_idx[0]),
    .S1(byte_idx[2]),
    .Z(_078_));
 gf180mcu_fd_sc_mcu9t5v0__nand2_1 _197_ (.A1(byte_idx[1]),
    .A2(_078_),
    .ZN(_079_));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_1 _198_ (.I(byte_idx[1]),
    .ZN(_080_));
 gf180mcu_fd_sc_mcu9t5v0__mux4_1 _199_ (.I0(byte_reg[0]),
    .I1(byte_reg[1]),
    .I2(byte_reg[4]),
    .I3(byte_reg[5]),
    .S0(byte_idx[0]),
    .S1(byte_idx[2]),
    .Z(_081_));
 gf180mcu_fd_sc_mcu9t5v0__nand2_1 _200_ (.A1(_080_),
    .A2(_081_),
    .ZN(_082_));
 gf180mcu_fd_sc_mcu9t5v0__aoi21_1 _201_ (.A1(_079_),
    .A2(_082_),
    .B(tx_state[6]),
    .ZN(_012_));
 gf180mcu_fd_sc_mcu9t5v0__nand2_1 _202_ (.A1(first_byte),
    .A2(tx_state[2]),
    .ZN(_083_));
 gf180mcu_fd_sc_mcu9t5v0__nor4_1 _203_ (.A1(byte_idx[0]),
    .A2(byte_idx[1]),
    .A3(byte_idx[2]),
    .A4(_083_),
    .ZN(_008_));
 gf180mcu_fd_sc_mcu9t5v0__nand2_1 _204_ (.A1(rx_bit_valid),
    .A2(rx_assembly_en),
    .ZN(_084_));
 gf180mcu_fd_sc_mcu9t5v0__nand2_1 _205_ (.A1(rx_shift[5]),
    .A2(_084_),
    .ZN(_085_));
 gf180mcu_fd_sc_mcu9t5v0__and2_4 _206_ (.A1(rx_bit_valid),
    .A2(rx_assembly_en),
    .Z(_086_));
 gf180mcu_fd_sc_mcu9t5v0__nand2_1 _208_ (.A1(rx_shift[6]),
    .A2(_086_),
    .ZN(_088_));
 gf180mcu_fd_sc_mcu9t5v0__nand2_2 _209_ (.A1(rx_receiving),
    .A2(_053_),
    .ZN(_089_));
 gf180mcu_fd_sc_mcu9t5v0__aoi21_1 _210_ (.A1(_085_),
    .A2(_088_),
    .B(_089_),
    .ZN(_014_));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_1 _211_ (.I(DataOut[6]),
    .ZN(_090_));
 gf180mcu_fd_sc_mcu9t5v0__nand2_1 _212_ (.A1(tx_state[2]),
    .A2(TxValid),
    .ZN(_091_));
 gf180mcu_fd_sc_mcu9t5v0__aoi22_4 _213_ (.A1(tx_state[2]),
    .A2(_074_),
    .B1(_091_),
    .B2(_061_),
    .ZN(_092_));
 gf180mcu_fd_sc_mcu9t5v0__nor2_1 _215_ (.A1(byte_reg[6]),
    .A2(_092_),
    .ZN(_094_));
 gf180mcu_fd_sc_mcu9t5v0__aoi211_1 _216_ (.A1(_090_),
    .A2(_092_),
    .B(_094_),
    .C(_052_),
    .ZN(_015_));
 gf180mcu_fd_sc_mcu9t5v0__and3_4 _217_ (.A1(rx_bitcnt[1]),
    .A2(rx_bitcnt[0]),
    .A3(_086_),
    .Z(_095_));
 gf180mcu_fd_sc_mcu9t5v0__and4_4 _218_ (.A1(rx_receiving),
    .A2(rx_bitcnt[2]),
    .A3(_053_),
    .A4(_095_),
    .Z(_096_));
 gf180mcu_fd_sc_mcu9t5v0__mux2_2 _220_ (.I0(DataIn[7]),
    .I1(rx_out_bit),
    .S(_096_),
    .Z(_016_));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_1 _221_ (.I(_089_),
    .ZN(_017_));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_1 _222_ (.I(DataOut[5]),
    .ZN(_097_));
 gf180mcu_fd_sc_mcu9t5v0__nor2_1 _223_ (.A1(byte_reg[5]),
    .A2(_092_),
    .ZN(_098_));
 gf180mcu_fd_sc_mcu9t5v0__aoi211_1 _224_ (.A1(_097_),
    .A2(_092_),
    .B(_098_),
    .C(_052_),
    .ZN(_018_));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_1 _225_ (.I(DataOut[4]),
    .ZN(_099_));
 gf180mcu_fd_sc_mcu9t5v0__nor2_1 _226_ (.A1(byte_reg[4]),
    .A2(_092_),
    .ZN(_100_));
 gf180mcu_fd_sc_mcu9t5v0__aoi211_1 _227_ (.A1(_099_),
    .A2(_092_),
    .B(_100_),
    .C(_052_),
    .ZN(_019_));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_1 _228_ (.I(DataOut[3]),
    .ZN(_101_));
 gf180mcu_fd_sc_mcu9t5v0__nor2_1 _229_ (.A1(byte_reg[3]),
    .A2(_092_),
    .ZN(_102_));
 gf180mcu_fd_sc_mcu9t5v0__aoi211_1 _230_ (.A1(_101_),
    .A2(_092_),
    .B(_102_),
    .C(_052_),
    .ZN(_020_));
 gf180mcu_fd_sc_mcu9t5v0__nand2_1 _231_ (.A1(rx_shift[7]),
    .A2(_084_),
    .ZN(_103_));
 gf180mcu_fd_sc_mcu9t5v0__nand2_1 _232_ (.A1(rx_out_bit),
    .A2(_086_),
    .ZN(_104_));
 gf180mcu_fd_sc_mcu9t5v0__aoi21_1 _233_ (.A1(_103_),
    .A2(_104_),
    .B(_089_),
    .ZN(_021_));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_1 _234_ (.I(DataOut[2]),
    .ZN(_105_));
 gf180mcu_fd_sc_mcu9t5v0__nor2_1 _235_ (.A1(byte_reg[2]),
    .A2(_092_),
    .ZN(_106_));
 gf180mcu_fd_sc_mcu9t5v0__aoi211_1 _236_ (.A1(_105_),
    .A2(_092_),
    .B(_106_),
    .C(_052_),
    .ZN(_022_));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_1 _237_ (.I(DataOut[1]),
    .ZN(_107_));
 gf180mcu_fd_sc_mcu9t5v0__nor2_1 _238_ (.A1(byte_reg[1]),
    .A2(_092_),
    .ZN(_108_));
 gf180mcu_fd_sc_mcu9t5v0__aoi211_1 _239_ (.A1(_107_),
    .A2(_092_),
    .B(_108_),
    .C(_052_),
    .ZN(_023_));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_1 _240_ (.I(DataOut[0]),
    .ZN(_109_));
 gf180mcu_fd_sc_mcu9t5v0__nor2_1 _241_ (.A1(byte_reg[0]),
    .A2(_092_),
    .ZN(_110_));
 gf180mcu_fd_sc_mcu9t5v0__aoi211_1 _242_ (.A1(_109_),
    .A2(_092_),
    .B(_110_),
    .C(_052_),
    .ZN(_024_));
 gf180mcu_fd_sc_mcu9t5v0__nand2_1 _243_ (.A1(rx_shift[4]),
    .A2(_084_),
    .ZN(_111_));
 gf180mcu_fd_sc_mcu9t5v0__nand2_1 _244_ (.A1(rx_shift[5]),
    .A2(_086_),
    .ZN(_112_));
 gf180mcu_fd_sc_mcu9t5v0__aoi21_1 _245_ (.A1(_111_),
    .A2(_112_),
    .B(_089_),
    .ZN(_025_));
 gf180mcu_fd_sc_mcu9t5v0__nand2_1 _246_ (.A1(rx_shift[3]),
    .A2(_084_),
    .ZN(_113_));
 gf180mcu_fd_sc_mcu9t5v0__nand2_1 _247_ (.A1(rx_shift[4]),
    .A2(_086_),
    .ZN(_114_));
 gf180mcu_fd_sc_mcu9t5v0__aoi21_1 _248_ (.A1(_113_),
    .A2(_114_),
    .B(_089_),
    .ZN(_026_));
 gf180mcu_fd_sc_mcu9t5v0__nand2_1 _249_ (.A1(rx_shift[2]),
    .A2(_084_),
    .ZN(_115_));
 gf180mcu_fd_sc_mcu9t5v0__nand2_1 _250_ (.A1(rx_shift[3]),
    .A2(_086_),
    .ZN(_116_));
 gf180mcu_fd_sc_mcu9t5v0__aoi21_1 _251_ (.A1(_115_),
    .A2(_116_),
    .B(_089_),
    .ZN(_027_));
 gf180mcu_fd_sc_mcu9t5v0__nand2_1 _252_ (.A1(rx_shift[1]),
    .A2(_084_),
    .ZN(_117_));
 gf180mcu_fd_sc_mcu9t5v0__nand2_1 _253_ (.A1(rx_shift[2]),
    .A2(_086_),
    .ZN(_118_));
 gf180mcu_fd_sc_mcu9t5v0__aoi21_1 _254_ (.A1(_117_),
    .A2(_118_),
    .B(_089_),
    .ZN(_028_));
 gf180mcu_fd_sc_mcu9t5v0__mux2_1 _255_ (.I0(tx_state[4]),
    .I1(TxValid),
    .S(tx_state[0]),
    .Z(_119_));
 gf180mcu_fd_sc_mcu9t5v0__and2_1 _256_ (.A1(sync_idx[0]),
    .A2(_119_),
    .Z(_120_));
 gf180mcu_fd_sc_mcu9t5v0__or2_1 _257_ (.A1(sync_idx[1]),
    .A2(_120_),
    .Z(_121_));
 gf180mcu_fd_sc_mcu9t5v0__aoi221_1 _258_ (.A1(_062_),
    .A2(entering_sync),
    .B1(_120_),
    .B2(sync_idx[1]),
    .C(_052_),
    .ZN(_122_));
 gf180mcu_fd_sc_mcu9t5v0__and2_1 _259_ (.A1(_121_),
    .A2(_122_),
    .Z(_029_));
 gf180mcu_fd_sc_mcu9t5v0__aoi21_1 _260_ (.A1(sync_idx[1]),
    .A2(_120_),
    .B(sync_idx[2]),
    .ZN(_123_));
 gf180mcu_fd_sc_mcu9t5v0__aoi211_1 _261_ (.A1(_064_),
    .A2(_119_),
    .B(_123_),
    .C(_052_),
    .ZN(_030_));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_1 _262_ (.I(first_byte),
    .ZN(_124_));
 gf180mcu_fd_sc_mcu9t5v0__oai22_1 _263_ (.A1(tx_state[2]),
    .A2(_061_),
    .B1(_092_),
    .B2(_124_),
    .ZN(_125_));
 gf180mcu_fd_sc_mcu9t5v0__and2_1 _264_ (.A1(_053_),
    .A2(_125_),
    .Z(_031_));
 gf180mcu_fd_sc_mcu9t5v0__nor2_1 _265_ (.A1(sync_idx[0]),
    .A2(_119_),
    .ZN(_126_));
 gf180mcu_fd_sc_mcu9t5v0__aoi211_1 _266_ (.A1(tx_state[4]),
    .A2(_120_),
    .B(_126_),
    .C(_052_),
    .ZN(_032_));
 gf180mcu_fd_sc_mcu9t5v0__xnor2_4 _267_ (.A1(rx_bitcnt[0]),
    .A2(_086_),
    .ZN(_127_));
 gf180mcu_fd_sc_mcu9t5v0__nor2_1 _268_ (.A1(_089_),
    .A2(_127_),
    .ZN(_033_));
 gf180mcu_fd_sc_mcu9t5v0__mux2_2 _269_ (.I0(DataIn[6]),
    .I1(rx_shift[7]),
    .S(_096_),
    .Z(_034_));
 gf180mcu_fd_sc_mcu9t5v0__mux2_2 _270_ (.I0(DataIn[5]),
    .I1(rx_shift[6]),
    .S(_096_),
    .Z(_035_));
 gf180mcu_fd_sc_mcu9t5v0__oai211_1 _271_ (.A1(rx_bitcnt[2]),
    .A2(_095_),
    .B(_053_),
    .C(rx_receiving),
    .ZN(_128_));
 gf180mcu_fd_sc_mcu9t5v0__aoi21_1 _272_ (.A1(rx_bitcnt[2]),
    .A2(_095_),
    .B(_128_),
    .ZN(_036_));
 gf180mcu_fd_sc_mcu9t5v0__mux2_2 _273_ (.I0(DataIn[4]),
    .I1(rx_shift[5]),
    .S(_096_),
    .Z(_037_));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_1 _274_ (.I(DataOut[7]),
    .ZN(_129_));
 gf180mcu_fd_sc_mcu9t5v0__nor2_1 _275_ (.A1(byte_reg[7]),
    .A2(_092_),
    .ZN(_130_));
 gf180mcu_fd_sc_mcu9t5v0__aoi211_1 _276_ (.A1(_129_),
    .A2(_092_),
    .B(_130_),
    .C(_052_),
    .ZN(_038_));
 gf180mcu_fd_sc_mcu9t5v0__mux2_2 _277_ (.I0(DataIn[3]),
    .I1(rx_shift[4]),
    .S(_096_),
    .Z(_039_));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_1 _278_ (.I(byte_idx[2]),
    .ZN(_131_));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_1 _279_ (.I(byte_idx[0]),
    .ZN(_132_));
 gf180mcu_fd_sc_mcu9t5v0__mux2_1 _280_ (.I0(tx_state[4]),
    .I1(stuff_consume),
    .S(tx_state[2]),
    .Z(_133_));
 gf180mcu_fd_sc_mcu9t5v0__oai221_2 _281_ (.A1(TxValid),
    .A2(_055_),
    .B1(_063_),
    .B2(_062_),
    .C(_133_),
    .ZN(_134_));
 gf180mcu_fd_sc_mcu9t5v0__or3_2 _282_ (.A1(_132_),
    .A2(_080_),
    .A3(_134_),
    .Z(_135_));
 gf180mcu_fd_sc_mcu9t5v0__nand3_1 _283_ (.A1(byte_idx[0]),
    .A2(byte_idx[1]),
    .A3(byte_idx[2]),
    .ZN(_136_));
 gf180mcu_fd_sc_mcu9t5v0__aoi21_1 _284_ (.A1(tx_state[2]),
    .A2(_136_),
    .B(_134_),
    .ZN(_137_));
 gf180mcu_fd_sc_mcu9t5v0__aoi211_2 _285_ (.A1(_131_),
    .A2(_135_),
    .B(_137_),
    .C(_052_),
    .ZN(_040_));
 gf180mcu_fd_sc_mcu9t5v0__mux2_2 _286_ (.I0(DataIn[2]),
    .I1(rx_shift[3]),
    .S(_096_),
    .Z(_042_));
 gf180mcu_fd_sc_mcu9t5v0__mux2_2 _287_ (.I0(DataIn[1]),
    .I1(rx_shift[2]),
    .S(_096_),
    .Z(_043_));
 gf180mcu_fd_sc_mcu9t5v0__mux2_2 _288_ (.I0(DataIn[0]),
    .I1(rx_shift[1]),
    .S(_096_),
    .Z(_044_));
 gf180mcu_fd_sc_mcu9t5v0__and2_1 _289_ (.A1(rx_stuff_err),
    .A2(_017_),
    .Z(_045_));
 gf180mcu_fd_sc_mcu9t5v0__nor3_1 _290_ (.A1(_010_),
    .A2(eop_pulse),
    .A3(bus_reset),
    .ZN(_138_));
 gf180mcu_fd_sc_mcu9t5v0__oai21_1 _291_ (.A1(sync_next),
    .A2(_138_),
    .B(_053_),
    .ZN(_139_));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_1 _292_ (.I(_139_),
    .ZN(_046_));
 gf180mcu_fd_sc_mcu9t5v0__oai21_1 _293_ (.A1(byte_idx[0]),
    .A2(byte_idx[1]),
    .B(tx_state[2]),
    .ZN(_140_));
 gf180mcu_fd_sc_mcu9t5v0__aoi21_1 _294_ (.A1(byte_idx[0]),
    .A2(byte_idx[1]),
    .B(_140_),
    .ZN(_141_));
 gf180mcu_fd_sc_mcu9t5v0__nor2_1 _295_ (.A1(_134_),
    .A2(_141_),
    .ZN(_142_));
 gf180mcu_fd_sc_mcu9t5v0__aoi211_1 _296_ (.A1(_080_),
    .A2(_134_),
    .B(_142_),
    .C(_052_),
    .ZN(_047_));
 gf180mcu_fd_sc_mcu9t5v0__nand4_1 _297_ (.A1(tx_state[2]),
    .A2(stuff_consume),
    .A3(_056_),
    .A4(_064_),
    .ZN(_143_));
 gf180mcu_fd_sc_mcu9t5v0__nor2_1 _298_ (.A1(_132_),
    .A2(_134_),
    .ZN(_144_));
 gf180mcu_fd_sc_mcu9t5v0__aoi211_1 _299_ (.A1(_132_),
    .A2(_143_),
    .B(_144_),
    .C(_052_),
    .ZN(_048_));
 gf180mcu_fd_sc_mcu9t5v0__aoi21_1 _300_ (.A1(rx_bitcnt[0]),
    .A2(_086_),
    .B(rx_bitcnt[1]),
    .ZN(_145_));
 gf180mcu_fd_sc_mcu9t5v0__nor3_1 _301_ (.A1(_089_),
    .A2(_095_),
    .A3(_145_),
    .ZN(_049_));
 gf180mcu_fd_sc_mcu9t5v0__nand2_1 _302_ (.A1(rx_shift[6]),
    .A2(_084_),
    .ZN(_146_));
 gf180mcu_fd_sc_mcu9t5v0__nand2_1 _303_ (.A1(rx_shift[7]),
    .A2(_086_),
    .ZN(_147_));
 gf180mcu_fd_sc_mcu9t5v0__aoi21_1 _304_ (.A1(_146_),
    .A2(_147_),
    .B(_089_),
    .ZN(_050_));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _305_ (.D(_024_),
    .CLK(clknet_3_7__leaf_clk),
    .Q(byte_reg[0]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _306_ (.D(_023_),
    .CLK(clknet_3_6__leaf_clk),
    .Q(byte_reg[1]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _307_ (.D(_022_),
    .CLK(clknet_3_7__leaf_clk),
    .Q(byte_reg[2]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _308_ (.D(_020_),
    .CLK(clknet_3_7__leaf_clk),
    .Q(byte_reg[3]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _309_ (.D(_019_),
    .CLK(clknet_3_6__leaf_clk),
    .Q(byte_reg[4]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _310_ (.D(_018_),
    .CLK(clknet_3_6__leaf_clk),
    .Q(byte_reg[5]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _311_ (.D(_015_),
    .CLK(clknet_3_7__leaf_clk),
    .Q(byte_reg[6]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _312_ (.D(_038_),
    .CLK(clknet_3_7__leaf_clk),
    .Q(byte_reg[7]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _313_ (.D(_045_),
    .CLK(clknet_3_3__leaf_clk),
    .Q(RxError));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _314_ (.D(_032_),
    .CLK(clknet_3_5__leaf_clk),
    .Q(sync_idx[0]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _315_ (.D(_029_),
    .CLK(clknet_3_5__leaf_clk),
    .Q(sync_idx[1]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _316_ (.D(_030_),
    .CLK(clknet_3_5__leaf_clk),
    .Q(sync_idx[2]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _317_ (.D(_048_),
    .CLK(clknet_3_7__leaf_clk),
    .Q(byte_idx[0]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _318_ (.D(_047_),
    .CLK(clknet_3_7__leaf_clk),
    .Q(byte_idx[1]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _319_ (.D(_040_),
    .CLK(clknet_3_7__leaf_clk),
    .Q(byte_idx[2]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _320_ (.D(_096_),
    .CLK(clknet_3_3__leaf_clk),
    .Q(RxValid));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _321_ (.D(_044_),
    .CLK(clknet_3_2__leaf_clk),
    .Q(DataIn[0]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _322_ (.D(_043_),
    .CLK(clknet_3_2__leaf_clk),
    .Q(DataIn[1]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _323_ (.D(_042_),
    .CLK(clknet_3_2__leaf_clk),
    .Q(DataIn[2]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _324_ (.D(_039_),
    .CLK(clknet_3_2__leaf_clk),
    .Q(DataIn[3]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _325_ (.D(_037_),
    .CLK(clknet_3_3__leaf_clk),
    .Q(DataIn[4]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _326_ (.D(_035_),
    .CLK(clknet_3_3__leaf_clk),
    .Q(DataIn[5]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _327_ (.D(_034_),
    .CLK(clknet_3_3__leaf_clk),
    .Q(DataIn[6]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _328_ (.D(_016_),
    .CLK(clknet_3_3__leaf_clk),
    .Q(DataIn[7]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _329_ (.D(_017_),
    .CLK(clknet_3_2__leaf_clk),
    .Q(rx_assembly_en));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _330_ (.D(_028_),
    .CLK(clknet_3_2__leaf_clk),
    .Q(rx_shift[1]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _331_ (.D(_027_),
    .CLK(clknet_3_2__leaf_clk),
    .Q(rx_shift[2]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _332_ (.D(_026_),
    .CLK(clknet_3_2__leaf_clk),
    .Q(rx_shift[3]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _333_ (.D(_025_),
    .CLK(clknet_3_2__leaf_clk),
    .Q(rx_shift[4]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _334_ (.D(_014_),
    .CLK(clknet_3_3__leaf_clk),
    .Q(rx_shift[5]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _335_ (.D(_050_),
    .CLK(clknet_3_3__leaf_clk),
    .Q(rx_shift[6]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _336_ (.D(_021_),
    .CLK(clknet_3_3__leaf_clk),
    .Q(rx_shift[7]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _337_ (.D(_031_),
    .CLK(clknet_3_7__leaf_clk),
    .Q(first_byte));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _338_ (.D(_033_),
    .CLK(clknet_3_2__leaf_clk),
    .Q(rx_bitcnt[0]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _339_ (.D(_049_),
    .CLK(clknet_3_2__leaf_clk),
    .Q(rx_bitcnt[1]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _340_ (.D(_036_),
    .CLK(clknet_3_2__leaf_clk),
    .Q(rx_bitcnt[2]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _341_ (.D(_046_),
    .CLK(clknet_3_1__leaf_clk),
    .Q(rx_receiving));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _342_ (.D(_004_),
    .CLK(clknet_3_6__leaf_clk),
    .Q(tx_state[0]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _343_ (.D(_005_),
    .CLK(clknet_3_6__leaf_clk),
    .Q(tx_state[1]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _344_ (.D(_006_),
    .CLK(clknet_3_5__leaf_clk),
    .Q(tx_state[2]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _345_ (.D(_000_),
    .CLK(clknet_3_3__leaf_clk),
    .Q(tx_state[3]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _346_ (.D(_007_),
    .CLK(clknet_3_5__leaf_clk),
    .Q(tx_state[4]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _347_ (.D(_001_),
    .CLK(clknet_3_3__leaf_clk),
    .Q(tx_state[5]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _348_ (.D(_002_),
    .CLK(clknet_3_5__leaf_clk),
    .Q(tx_state[6]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 _349_ (.D(_003_),
    .CLK(clknet_3_6__leaf_clk),
    .Q(tx_state[7]));
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
 gf180mcu_fd_sc_mcu9t5v0__inv_4 clkload0 (.I(clknet_3_0__leaf_clk));
 gf180mcu_fd_sc_mcu9t5v0__inv_4 clkload1 (.I(clknet_3_1__leaf_clk));
 gf180mcu_fd_sc_mcu9t5v0__inv_3 clkload2 (.I(clknet_3_3__leaf_clk));
 gf180mcu_fd_sc_mcu9t5v0__inv_8 clkload3 (.I(clknet_3_4__leaf_clk));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_8 clkload4 (.I(clknet_3_5__leaf_clk));
 gf180mcu_fd_sc_mcu9t5v0__inv_4 clkload5 (.I(clknet_3_6__leaf_clk));
 gf180mcu_fd_sc_mcu9t5v0__inv_4 clkload6 (.I(clknet_3_7__leaf_clk));
 gf180mcu_fd_sc_mcu9t5v0__nand2_4 \u_decoder/_05_  (.A1(dec_bit_strobe),
    .A2(dec_bit_strobe),
    .ZN(\u_decoder/_04_ ));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_1 \u_decoder/_06_  (.I(\u_decoder/_04_ ),
    .ZN(\u_decoder/_00_ ));
 gf180mcu_fd_sc_mcu9t5v0__mux2_1 \u_decoder/_07_  (.I0(dec_bit_level),
    .I1(\u_decoder/prev_level ),
    .S(\u_decoder/_04_ ),
    .Z(\u_decoder/_01_ ));
 gf180mcu_fd_sc_mcu9t5v0__xnor2_1 \u_decoder/_08_  (.A1(dec_bit_level),
    .A2(\u_decoder/prev_level ),
    .ZN(\u_decoder/_03_ ));
 gf180mcu_fd_sc_mcu9t5v0__mux2_2 \u_decoder/_09_  (.I0(\u_decoder/_03_ ),
    .I1(dec_data_bit),
    .S(\u_decoder/_04_ ),
    .Z(\u_decoder/_02_ ));
 gf180mcu_fd_sc_mcu9t5v0__dffsnq_1 \u_decoder/_10_  (.D(\u_decoder/_01_ ),
    .SETN(_053_),
    .CLK(clknet_3_1__leaf_clk),
    .Q(\u_decoder/prev_level ));
 gf180mcu_fd_sc_mcu9t5v0__dffrnq_1 \u_decoder/_11_  (.D(\u_decoder/_02_ ),
    .RN(_053_),
    .CLK(clknet_3_0__leaf_clk),
    .Q(dec_data_bit));
 gf180mcu_fd_sc_mcu9t5v0__dffrnq_1 \u_decoder/_12_  (.D(\u_decoder/_00_ ),
    .RN(_053_),
    .CLK(clknet_3_0__leaf_clk),
    .Q(dec_data_strobe));
 gf180mcu_fd_sc_mcu9t5v0__nand2_4 \u_destuffer/_16_  (.A1(\u_destuffer/ones_run [1]),
    .A2(\u_destuffer/ones_run [2]),
    .ZN(\u_destuffer/_06_ ));
 gf180mcu_fd_sc_mcu9t5v0__nor2_2 \u_destuffer/_17_  (.A1(\u_destuffer/ones_run [0]),
    .A2(\u_destuffer/_06_ ),
    .ZN(\u_destuffer/_07_ ));
 gf180mcu_fd_sc_mcu9t5v0__inv_2 \u_destuffer/_18_  (.I(dec_data_strobe),
    .ZN(\u_destuffer/_08_ ));
 gf180mcu_fd_sc_mcu9t5v0__aoi21_4 \u_destuffer/_19_  (.A1(rx_receiving),
    .A2(\u_destuffer/_07_ ),
    .B(\u_destuffer/_08_ ),
    .ZN(\u_destuffer/_00_ ));
 gf180mcu_fd_sc_mcu9t5v0__and4_1 \u_destuffer/_20_  (.A1(dec_data_strobe),
    .A2(rx_receiving),
    .A3(dec_data_bit),
    .A4(\u_destuffer/_07_ ),
    .Z(\u_destuffer/_01_ ));
 gf180mcu_fd_sc_mcu9t5v0__and3_2 \u_destuffer/_21_  (.A1(rx_receiving),
    .A2(dec_data_bit),
    .A3(\u_destuffer/_06_ ),
    .Z(\u_destuffer/_09_ ));
 gf180mcu_fd_sc_mcu9t5v0__aoi21_2 \u_destuffer/_22_  (.A1(\u_destuffer/_08_ ),
    .A2(rx_receiving),
    .B(\u_destuffer/_09_ ),
    .ZN(\u_destuffer/_10_ ));
 gf180mcu_fd_sc_mcu9t5v0__inv_2 \u_destuffer/_23_  (.I(\u_destuffer/ones_run [0]),
    .ZN(\u_destuffer/_11_ ));
 gf180mcu_fd_sc_mcu9t5v0__aoi21_4 \u_destuffer/_24_  (.A1(\u_destuffer/_08_ ),
    .A2(rx_receiving),
    .B(\u_destuffer/_11_ ),
    .ZN(\u_destuffer/_12_ ));
 gf180mcu_fd_sc_mcu9t5v0__xnor2_1 \u_destuffer/_25_  (.A1(\u_destuffer/ones_run [1]),
    .A2(\u_destuffer/_12_ ),
    .ZN(\u_destuffer/_13_ ));
 gf180mcu_fd_sc_mcu9t5v0__nor2_2 \u_destuffer/_26_  (.A1(\u_destuffer/_10_ ),
    .A2(\u_destuffer/_13_ ),
    .ZN(\u_destuffer/_02_ ));
 gf180mcu_fd_sc_mcu9t5v0__mux2_2 \u_destuffer/_27_  (.I0(rx_out_bit),
    .I1(dec_data_bit),
    .S(\u_destuffer/_00_ ),
    .Z(\u_destuffer/_03_ ));
 gf180mcu_fd_sc_mcu9t5v0__aoi21_1 \u_destuffer/_28_  (.A1(\u_destuffer/ones_run [1]),
    .A2(\u_destuffer/_12_ ),
    .B(\u_destuffer/ones_run [2]),
    .ZN(\u_destuffer/_14_ ));
 gf180mcu_fd_sc_mcu9t5v0__nor2_1 \u_destuffer/_29_  (.A1(\u_destuffer/_10_ ),
    .A2(\u_destuffer/_14_ ),
    .ZN(\u_destuffer/_04_ ));
 gf180mcu_fd_sc_mcu9t5v0__aoi21_1 \u_destuffer/_30_  (.A1(dec_data_strobe),
    .A2(\u_destuffer/_09_ ),
    .B(\u_destuffer/ones_run [0]),
    .ZN(\u_destuffer/_15_ ));
 gf180mcu_fd_sc_mcu9t5v0__nor2_1 \u_destuffer/_31_  (.A1(\u_destuffer/_12_ ),
    .A2(\u_destuffer/_15_ ),
    .ZN(\u_destuffer/_05_ ));
 gf180mcu_fd_sc_mcu9t5v0__dffrnq_1 \u_destuffer/_32_  (.D(\u_destuffer/_03_ ),
    .RN(_053_),
    .CLK(clknet_3_0__leaf_clk),
    .Q(rx_out_bit));
 gf180mcu_fd_sc_mcu9t5v0__dffrnq_1 \u_destuffer/_33_  (.D(\u_destuffer/_05_ ),
    .RN(_053_),
    .CLK(clknet_3_0__leaf_clk),
    .Q(\u_destuffer/ones_run [0]));
 gf180mcu_fd_sc_mcu9t5v0__dffrnq_1 \u_destuffer/_34_  (.D(\u_destuffer/_02_ ),
    .RN(_053_),
    .CLK(clknet_3_2__leaf_clk),
    .Q(\u_destuffer/ones_run [1]));
 gf180mcu_fd_sc_mcu9t5v0__dffrnq_1 \u_destuffer/_35_  (.D(\u_destuffer/_04_ ),
    .RN(_053_),
    .CLK(clknet_3_2__leaf_clk),
    .Q(\u_destuffer/ones_run [2]));
 gf180mcu_fd_sc_mcu9t5v0__dffrnq_1 \u_destuffer/_36_  (.D(\u_destuffer/_00_ ),
    .RN(_053_),
    .CLK(clknet_3_2__leaf_clk),
    .Q(rx_bit_valid));
 gf180mcu_fd_sc_mcu9t5v0__dffrnq_1 \u_destuffer/_37_  (.D(\u_destuffer/_01_ ),
    .RN(_053_),
    .CLK(clknet_3_0__leaf_clk),
    .Q(rx_stuff_err));
 gf180mcu_fd_sc_mcu9t5v0__nor3_4 \u_encoder/_3_  (.A1(_009_),
    .A2(nrzi_level),
    .A3(entering_sync),
    .ZN(\u_encoder/_1_ ));
 gf180mcu_fd_sc_mcu9t5v0__xor2_2 \u_encoder/_4_  (.A1(_013_),
    .A2(\u_encoder/_1_ ),
    .Z(\u_encoder/_2_ ));
 gf180mcu_fd_sc_mcu9t5v0__mux2_2 \u_encoder/_5_  (.I0(nrzi_level),
    .I1(\u_encoder/_2_ ),
    .S(_011_),
    .Z(\u_encoder/_0_ ));
 gf180mcu_fd_sc_mcu9t5v0__dffsnq_1 \u_encoder/_6_  (.D(\u_encoder/_0_ ),
    .SETN(_053_),
    .CLK(clknet_3_4__leaf_clk),
    .Q(nrzi_level));
 gf180mcu_fd_sc_mcu9t5v0__nor2_1 \u_eop_detector/_27_  (.A1(line_state[0]),
    .A2(line_state[1]),
    .ZN(\u_eop_detector/_08_ ));
 gf180mcu_fd_sc_mcu9t5v0__nand2_1 \u_eop_detector/_28_  (.A1(_053_),
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
    .CLK(clknet_3_1__leaf_clk),
    .Q(bus_reset));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 \u_eop_detector/_55_  (.D(\u_eop_detector/_07_ ),
    .CLK(clknet_3_1__leaf_clk),
    .Q(eop_pulse));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 \u_eop_detector/_56_  (.D(\u_eop_detector/_03_ ),
    .CLK(clknet_3_4__leaf_clk),
    .Q(\u_eop_detector/se0_count [0]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 \u_eop_detector/_57_  (.D(\u_eop_detector/_02_ ),
    .CLK(clknet_3_1__leaf_clk),
    .Q(\u_eop_detector/se0_count [1]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 \u_eop_detector/_58_  (.D(\u_eop_detector/_01_ ),
    .CLK(clknet_3_0__leaf_clk),
    .Q(\u_eop_detector/se0_count [2]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 \u_eop_detector/_59_  (.D(\u_eop_detector/_05_ ),
    .CLK(clknet_3_1__leaf_clk),
    .Q(\u_eop_detector/se0_count [3]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 \u_eop_detector/_60_  (.D(\u_eop_detector/_04_ ),
    .CLK(clknet_3_1__leaf_clk),
    .Q(\u_eop_detector/se0_count [4]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 \u_eop_detector/_61_  (.D(\u_eop_detector/_06_ ),
    .CLK(clknet_3_4__leaf_clk),
    .Q(\u_eop_detector/se0_count [5]));
 gf180mcu_fd_sc_mcu9t5v0__inv_2 \u_line_state/_3_  (.I(rxdp),
    .ZN(\u_line_state/_2_ ));
 gf180mcu_fd_sc_mcu9t5v0__nand2_1 \u_line_state/_4_  (.A1(\u_line_state/_2_ ),
    .A2(_053_),
    .ZN(\u_line_state/_0_ ));
 gf180mcu_fd_sc_mcu9t5v0__and2_4 \u_line_state/_5_  (.A1(_053_),
    .A2(rxdm),
    .Z(\u_line_state/_1_ ));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 \u_line_state/_6_  (.D(\u_line_state/_0_ ),
    .CLK(clknet_3_6__leaf_clk),
    .Q(line_state[0]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 \u_line_state/_7_  (.D(\u_line_state/_1_ ),
    .CLK(clknet_3_6__leaf_clk),
    .Q(line_state[1]));
 gf180mcu_fd_sc_mcu9t5v0__inv_3 \u_stuffer/_14_  (.I(\u_stuffer/run [0]),
    .ZN(\u_stuffer/_03_ ));
 gf180mcu_fd_sc_mcu9t5v0__nor2_4 \u_stuffer/_15_  (.A1(raw_mode),
    .A2(_008_),
    .ZN(\u_stuffer/_04_ ));
 gf180mcu_fd_sc_mcu9t5v0__nand4_4 \u_stuffer/_16_  (.A1(\u_stuffer/run [1]),
    .A2(\u_stuffer/_03_ ),
    .A3(\u_stuffer/run [2]),
    .A4(\u_stuffer/_04_ ),
    .ZN(stuff_consume));
 gf180mcu_fd_sc_mcu9t5v0__and2_1 \u_stuffer/_17_  (.A1(_012_),
    .A2(stuff_consume),
    .Z(stuff_bit_out));
 gf180mcu_fd_sc_mcu9t5v0__nand3_1 \u_stuffer/_18_  (.A1(\u_stuffer/run [2]),
    .A2(_012_),
    .A3(\u_stuffer/_04_ ),
    .ZN(\u_stuffer/_05_ ));
 gf180mcu_fd_sc_mcu9t5v0__nor3_1 \u_stuffer/_19_  (.A1(\u_stuffer/run [1]),
    .A2(\u_stuffer/_03_ ),
    .A3(\u_stuffer/_05_ ),
    .ZN(stuff_pending_after));
 gf180mcu_fd_sc_mcu9t5v0__aoi21_2 \u_stuffer/_20_  (.A1(\u_stuffer/_03_ ),
    .A2(stuff_consume),
    .B(_008_),
    .ZN(\u_stuffer/_06_ ));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_1 \u_stuffer/_21_  (.I(raw_mode),
    .ZN(\u_stuffer/_07_ ));
 gf180mcu_fd_sc_mcu9t5v0__nand3_1 \u_stuffer/_22_  (.A1(\u_stuffer/_07_ ),
    .A2(_012_),
    .A3(tx_body_active),
    .ZN(\u_stuffer/_08_ ));
 gf180mcu_fd_sc_mcu9t5v0__oai22_1 \u_stuffer/_23_  (.A1(\u_stuffer/_03_ ),
    .A2(tx_body_active),
    .B1(\u_stuffer/_06_ ),
    .B2(\u_stuffer/_08_ ),
    .ZN(\u_stuffer/_00_ ));
 gf180mcu_fd_sc_mcu9t5v0__nand3_2 \u_stuffer/_24_  (.A1(_012_),
    .A2(\u_stuffer/_04_ ),
    .A3(stuff_consume),
    .ZN(\u_stuffer/_09_ ));
 gf180mcu_fd_sc_mcu9t5v0__nand2_2 \u_stuffer/_25_  (.A1(\u_stuffer/run [0]),
    .A2(tx_body_active),
    .ZN(\u_stuffer/_10_ ));
 gf180mcu_fd_sc_mcu9t5v0__xor2_1 \u_stuffer/_26_  (.A1(\u_stuffer/run [1]),
    .A2(\u_stuffer/_10_ ),
    .Z(\u_stuffer/_11_ ));
 gf180mcu_fd_sc_mcu9t5v0__aoi21_2 \u_stuffer/_27_  (.A1(tx_body_active),
    .A2(\u_stuffer/_09_ ),
    .B(\u_stuffer/_11_ ),
    .ZN(\u_stuffer/_01_ ));
 gf180mcu_fd_sc_mcu9t5v0__nand3_2 \u_stuffer/_28_  (.A1(\u_stuffer/run [1]),
    .A2(\u_stuffer/run [0]),
    .A3(tx_body_active),
    .ZN(\u_stuffer/_12_ ));
 gf180mcu_fd_sc_mcu9t5v0__xor2_2 \u_stuffer/_29_  (.A1(\u_stuffer/run [2]),
    .A2(\u_stuffer/_12_ ),
    .Z(\u_stuffer/_13_ ));
 gf180mcu_fd_sc_mcu9t5v0__aoi21_2 \u_stuffer/_30_  (.A1(tx_body_active),
    .A2(\u_stuffer/_09_ ),
    .B(\u_stuffer/_13_ ),
    .ZN(\u_stuffer/_02_ ));
 gf180mcu_fd_sc_mcu9t5v0__dffrnq_1 \u_stuffer/_31_  (.D(\u_stuffer/_00_ ),
    .RN(_053_),
    .CLK(clknet_3_5__leaf_clk),
    .Q(\u_stuffer/run [0]));
 gf180mcu_fd_sc_mcu9t5v0__dffrnq_1 \u_stuffer/_32_  (.D(\u_stuffer/_01_ ),
    .RN(_053_),
    .CLK(clknet_3_4__leaf_clk),
    .Q(\u_stuffer/run [1]));
 gf180mcu_fd_sc_mcu9t5v0__dffrnq_1 \u_stuffer/_33_  (.D(\u_stuffer/_02_ ),
    .RN(_053_),
    .CLK(clknet_3_4__leaf_clk),
    .Q(\u_stuffer/run [2]));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_1 \u_sync_detector/_16_  (.I(_010_),
    .ZN(\u_sync_detector/_05_ ));
 gf180mcu_fd_sc_mcu9t5v0__nand3_4 \u_sync_detector/_17_  (.A1(\u_sync_detector/match [0]),
    .A2(\u_sync_detector/match [1]),
    .A3(\u_sync_detector/match [2]),
    .ZN(\u_sync_detector/_06_ ));
 gf180mcu_fd_sc_mcu9t5v0__nand2_4 \u_sync_detector/_18_  (.A1(dec_data_strobe),
    .A2(dec_data_bit),
    .ZN(\u_sync_detector/_07_ ));
 gf180mcu_fd_sc_mcu9t5v0__nor4_4 \u_sync_detector/_19_  (.A1(\u_sync_detector/match [3]),
    .A2(\u_sync_detector/_05_ ),
    .A3(\u_sync_detector/_06_ ),
    .A4(\u_sync_detector/_07_ ),
    .ZN(sync_next));
 gf180mcu_fd_sc_mcu9t5v0__clkinv_1 \u_sync_detector/_20_  (.I(\u_sync_detector/match [3]),
    .ZN(\u_sync_detector/_08_ ));
 gf180mcu_fd_sc_mcu9t5v0__nand3_4 \u_sync_detector/_21_  (.A1(_010_),
    .A2(_053_),
    .A3(\u_sync_detector/_07_ ),
    .ZN(\u_sync_detector/_09_ ));
 gf180mcu_fd_sc_mcu9t5v0__and3_2 \u_sync_detector/_22_  (.A1(\u_sync_detector/match [0]),
    .A2(dec_data_strobe),
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
    .A2(dec_data_strobe),
    .Z(\u_sync_detector/_13_ ));
 gf180mcu_fd_sc_mcu9t5v0__nor2_1 \u_sync_detector/_28_  (.A1(\u_sync_detector/match [1]),
    .A2(\u_sync_detector/_13_ ),
    .ZN(\u_sync_detector/_14_ ));
 gf180mcu_fd_sc_mcu9t5v0__nor3_1 \u_sync_detector/_29_  (.A1(\u_sync_detector/_09_ ),
    .A2(\u_sync_detector/_10_ ),
    .A3(\u_sync_detector/_14_ ),
    .ZN(\u_sync_detector/_02_ ));
 gf180mcu_fd_sc_mcu9t5v0__nor2_1 \u_sync_detector/_30_  (.A1(\u_sync_detector/match [0]),
    .A2(dec_data_strobe),
    .ZN(\u_sync_detector/_15_ ));
 gf180mcu_fd_sc_mcu9t5v0__aoi211_1 \u_sync_detector/_31_  (.A1(\u_sync_detector/_06_ ),
    .A2(\u_sync_detector/_13_ ),
    .B(\u_sync_detector/_15_ ),
    .C(\u_sync_detector/_09_ ),
    .ZN(\u_sync_detector/_03_ ));
 gf180mcu_fd_sc_mcu9t5v0__and2_2 \u_sync_detector/_32_  (.A1(_053_),
    .A2(sync_next),
    .Z(\u_sync_detector/_04_ ));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 \u_sync_detector/_33_  (.D(\u_sync_detector/_04_ ),
    .CLK(clknet_3_1__leaf_clk),
    .Q(\u_sync_detector/sync_valid ));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 \u_sync_detector/_34_  (.D(\u_sync_detector/_03_ ),
    .CLK(clknet_3_0__leaf_clk),
    .Q(\u_sync_detector/match [0]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 \u_sync_detector/_35_  (.D(\u_sync_detector/_02_ ),
    .CLK(clknet_3_0__leaf_clk),
    .Q(\u_sync_detector/match [1]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 \u_sync_detector/_36_  (.D(\u_sync_detector/_01_ ),
    .CLK(clknet_3_0__leaf_clk),
    .Q(\u_sync_detector/match [2]));
 gf180mcu_fd_sc_mcu9t5v0__dffq_1 \u_sync_detector/_37_  (.D(\u_sync_detector/_00_ ),
    .CLK(clknet_3_1__leaf_clk),
    .Q(\u_sync_detector/match [3]));
 assign LineState[0] = line_state[0];
 assign LineState[1] = line_state[1];
 assign RxActive = rx_receiving;
endmodule
