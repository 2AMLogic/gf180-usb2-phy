v {xschem version=3.4.7 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
T {differential_driver -- USB 2.0 FS single-ended DP/DM output stages (spec Sec.6)
Two symmetric single-ended drivers (DP half, DM half). Each: a small
CMOS predriver -> RC gate-slew resistor -> large complementary output
stage -> series output resistor (rm1) to the pad. TXDP/TXDM are opaque
digital inputs from the (out-of-scope) NRZI/encode logic; this cell
defines TXDx=1 => Dx driven high (net non-inversion: predriver inverts
once, the output stage's shared-gate CMOS pair inverts again).
TXOE (active-high) is the output enable: TXOE=0 turns BOTH output
transistors off on BOTH pads (DP/DM high-Z) for every TXDP/TXDM value.
Because the output stage's PMOS and NMOS share no gate net any more,
each half has two gated predrivers: NAND(TXDx,TXOE) -> R_slew -> PMOS
gate (held at VDD when disabled) and NOR(TXDx,!TXOE) -> R_slew -> NMOS
gate (held at VSS when disabled). With TXOE=1 each reduces to the old
inverter, so the output-stage topology is unchanged; the gate load is
split across two equal slew resistors. See design/README.md (#114).
Design-intent targets (NOT yet PVT-simulated -- see #26):
  rise/fall 10-90% into 50pF: 4-20ns   (Sec.6)
  rise/fall matching: within 10%        (Sec.6)
  crossover voltage: 1.3-2.0V            (Sec.6)
  output resistance: 28-44 ohm           (Sec.6)} -900 -900 0 0 0.35 0.35 {}
T {Sizing rationale (first-order, hand calc -- to be confirmed by #26 PVT sim):
Output stage Wp:Wn = 2:1 (gf180mcu 3.3V mobility ratio) for rise/fall
matching and a crossover point near VDD/2 = 1.65V, inside [1.3,2.0]V.
R_series (rm1, metal1) sized 36 ohm nominal (L/W=400, e.g. W=2u L=800u):
rm1 sheet-rho process spread is only +/-13% (rsh_rm1=0.09+/-0.012 ohm/sq,
see libs.tech/ngspice/sm141064.ngspice) -- comfortably inside the
spec's +/-22%-wide 28-44 ohm band without a trim network (contrast with
the D+ pull-up in dplus_pullup.sch, whose +/-5% target IS tighter than
untrimmed poly/metal spread and needs a trim ladder).
R_series alone into 50pF gives a floor of ~2.2*36ohm*50pF=3.96ns (10-90%),
right at the lower spec edge; R_slew (poly, ~4kohm) into the big output
FET's gate cap adds a second RC stage so the edge lands mid-window
instead of at the floor -- this is the 'why' for R_slew's existence.} -900 -700 0 0 0.3 0.3 {}
N -1080 -530 -1080 -570 {}
C {devices/lab_pin.sym} -1080 -570 0 0 {name=l1 lab=VDD}
N -1080 -470 -1080 -430 {}
C {devices/lab_pin.sym} -1080 -430 0 0 {name=l2 lab=TXOEB}
N -1120 -500 -1180 -500 {}
C {devices/lab_pin.sym} -1180 -500 0 0 {name=l3 lab=TXOE}
N -1080 -500 -1020 -500 {}
C {devices/lab_pin.sym} -1020 -500 0 0 {name=l4 lab=VDD}
C {symbols/pfet_03v3.sym} -1100 -500 0 0 {name=MPOEB
L=0.28u
W=4u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N -880 -530 -880 -570 {}
C {devices/lab_pin.sym} -880 -570 0 0 {name=l5 lab=TXOEB}
N -880 -470 -880 -430 {}
C {devices/lab_pin.sym} -880 -430 0 0 {name=l6 lab=VSS}
N -920 -500 -980 -500 {}
C {devices/lab_pin.sym} -980 -500 0 0 {name=l7 lab=TXOE}
N -880 -500 -820 -500 {}
C {devices/lab_pin.sym} -820 -500 0 0 {name=l8 lab=VSS}
C {symbols/nfet_03v3.sym} -900 -500 0 0 {name=MNOEB
L=0.28u
W=2u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N -980 -30 -980 -70 {}
C {devices/lab_pin.sym} -980 -70 0 0 {name=l9 lab=VDD}
N -980 30 -980 70 {}
C {devices/lab_pin.sym} -980 70 0 0 {name=l10 lab=DP_PREP}
N -1020 0 -1080 0 {}
C {devices/lab_pin.sym} -1080 0 0 0 {name=l11 lab=TXDP}
N -980 0 -920 0 {}
C {devices/lab_pin.sym} -920 0 0 0 {name=l12 lab=VDD}
C {symbols/pfet_03v3.sym} -1000 0 0 0 {name=MP1ADP
L=0.28u
W=4u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N -720 -30 -720 -70 {}
C {devices/lab_pin.sym} -720 -70 0 0 {name=l13 lab=VDD}
N -720 30 -720 70 {}
C {devices/lab_pin.sym} -720 70 0 0 {name=l14 lab=DP_PREP}
N -760 0 -820 0 {}
C {devices/lab_pin.sym} -820 0 0 0 {name=l15 lab=TXOE}
N -720 0 -660 0 {}
C {devices/lab_pin.sym} -660 0 0 0 {name=l16 lab=VDD}
C {symbols/pfet_03v3.sym} -740 0 0 0 {name=MP1BDP
L=0.28u
W=4u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N -460 -30 -460 -70 {}
C {devices/lab_pin.sym} -460 -70 0 0 {name=l17 lab=DP_PREP}
N -460 30 -460 70 {}
C {devices/lab_pin.sym} -460 70 0 0 {name=l18 lab=DP_NX}
N -500 0 -560 0 {}
C {devices/lab_pin.sym} -560 0 0 0 {name=l19 lab=TXDP}
N -460 0 -400 0 {}
C {devices/lab_pin.sym} -400 0 0 0 {name=l20 lab=VSS}
C {symbols/nfet_03v3.sym} -480 0 0 0 {name=MN1ADP
L=0.28u
W=4u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N -200 -30 -200 -70 {}
C {devices/lab_pin.sym} -200 -70 0 0 {name=l21 lab=DP_NX}
N -200 30 -200 70 {}
C {devices/lab_pin.sym} -200 70 0 0 {name=l22 lab=VSS}
N -240 0 -300 0 {}
C {devices/lab_pin.sym} -300 0 0 0 {name=l23 lab=TXOE}
N -200 0 -140 0 {}
C {devices/lab_pin.sym} -140 0 0 0 {name=l24 lab=VSS}
C {symbols/nfet_03v3.sym} -220 0 0 0 {name=MN1BDP
L=0.28u
W=4u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N 40 -30 40 -70 {}
C {devices/lab_pin.sym} 40 -70 0 0 {name=l25 lab=DP_PREP}
N 40 30 40 70 {}
C {devices/lab_pin.sym} 40 70 0 0 {name=l26 lab=DP_GATEP}
N 20 0 -40 0 {}
C {devices/lab_pin.sym} -40 0 0 0 {name=l27 lab=VSS}
C {symbols/ppolyf_u.sym} 40 0 0 0 {name=RSLEWPDP
W=1u
L=2u
model=ppolyf_u
spiceprefix=X
m=1
}
N -980 270 -980 230 {}
C {devices/lab_pin.sym} -980 230 0 0 {name=l28 lab=VDD}
N -980 330 -980 370 {}
C {devices/lab_pin.sym} -980 370 0 0 {name=l29 lab=DP_PX}
N -1020 300 -1080 300 {}
C {devices/lab_pin.sym} -1080 300 0 0 {name=l30 lab=TXDP}
N -980 300 -920 300 {}
C {devices/lab_pin.sym} -920 300 0 0 {name=l31 lab=VDD}
C {symbols/pfet_03v3.sym} -1000 300 0 0 {name=MP3ADP
L=0.28u
W=8u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N -720 270 -720 230 {}
C {devices/lab_pin.sym} -720 230 0 0 {name=l32 lab=DP_PX}
N -720 330 -720 370 {}
C {devices/lab_pin.sym} -720 370 0 0 {name=l33 lab=DP_PREN}
N -760 300 -820 300 {}
C {devices/lab_pin.sym} -820 300 0 0 {name=l34 lab=TXOEB}
N -720 300 -660 300 {}
C {devices/lab_pin.sym} -660 300 0 0 {name=l35 lab=VDD}
C {symbols/pfet_03v3.sym} -740 300 0 0 {name=MP3BDP
L=0.28u
W=8u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N -460 270 -460 230 {}
C {devices/lab_pin.sym} -460 230 0 0 {name=l36 lab=DP_PREN}
N -460 330 -460 370 {}
C {devices/lab_pin.sym} -460 370 0 0 {name=l37 lab=VSS}
N -500 300 -560 300 {}
C {devices/lab_pin.sym} -560 300 0 0 {name=l38 lab=TXDP}
N -460 300 -400 300 {}
C {devices/lab_pin.sym} -400 300 0 0 {name=l39 lab=VSS}
C {symbols/nfet_03v3.sym} -480 300 0 0 {name=MN3ADP
L=0.28u
W=2u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N -200 270 -200 230 {}
C {devices/lab_pin.sym} -200 230 0 0 {name=l40 lab=DP_PREN}
N -200 330 -200 370 {}
C {devices/lab_pin.sym} -200 370 0 0 {name=l41 lab=VSS}
N -240 300 -300 300 {}
C {devices/lab_pin.sym} -300 300 0 0 {name=l42 lab=TXOEB}
N -200 300 -140 300 {}
C {devices/lab_pin.sym} -140 300 0 0 {name=l43 lab=VSS}
C {symbols/nfet_03v3.sym} -220 300 0 0 {name=MN3BDP
L=0.28u
W=2u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N 40 270 40 230 {}
C {devices/lab_pin.sym} 40 230 0 0 {name=l44 lab=DP_PREN}
N 40 330 40 370 {}
C {devices/lab_pin.sym} 40 370 0 0 {name=l45 lab=DP_GATEN}
N 20 300 -40 300 {}
C {devices/lab_pin.sym} -40 300 0 0 {name=l46 lab=VSS}
C {symbols/ppolyf_u.sym} 40 300 0 0 {name=RSLEWNDP
W=1u
L=2u
model=ppolyf_u
spiceprefix=X
m=1
}
N -980 570 -980 530 {}
C {devices/lab_pin.sym} -980 530 0 0 {name=l47 lab=VDD}
N -980 630 -980 670 {}
C {devices/lab_pin.sym} -980 670 0 0 {name=l48 lab=DP_OUTINT}
N -1020 600 -1080 600 {}
C {devices/lab_pin.sym} -1080 600 0 0 {name=l49 lab=DP_GATEP}
N -980 600 -920 600 {}
C {devices/lab_pin.sym} -920 600 0 0 {name=l50 lab=VDD}
C {symbols/pfet_03v3.sym} -1000 600 0 0 {name=MP2DP
L=0.28u
W=60u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N -720 570 -720 530 {}
C {devices/lab_pin.sym} -720 530 0 0 {name=l51 lab=DP_OUTINT}
N -720 630 -720 670 {}
C {devices/lab_pin.sym} -720 670 0 0 {name=l52 lab=VSS}
N -760 600 -820 600 {}
C {devices/lab_pin.sym} -820 600 0 0 {name=l53 lab=DP_GATEN}
N -720 600 -660 600 {}
C {devices/lab_pin.sym} -660 600 0 0 {name=l54 lab=VSS}
C {symbols/nfet_03v3.sym} -740 600 0 0 {name=MN2DP
L=0.28u
W=30u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N -480 570 -480 530 {}
C {devices/lab_pin.sym} -480 530 0 0 {name=l55 lab=DP_OUTINT}
N -480 630 -480 670 {}
C {devices/lab_pin.sym} -480 670 0 0 {name=l56 lab=DP}
C {symbols/rm1.sym} -480 600 0 0 {name=RSERDP
W=2u
L=800u
model=rm1
spiceprefix=X
m=1
}
N 1020 -30 1020 -70 {}
C {devices/lab_pin.sym} 1020 -70 0 0 {name=l57 lab=VDD}
N 1020 30 1020 70 {}
C {devices/lab_pin.sym} 1020 70 0 0 {name=l58 lab=DM_PREP}
N 980 0 920 0 {}
C {devices/lab_pin.sym} 920 0 0 0 {name=l59 lab=TXDM}
N 1020 0 1080 0 {}
C {devices/lab_pin.sym} 1080 0 0 0 {name=l60 lab=VDD}
C {symbols/pfet_03v3.sym} 1000 0 0 0 {name=MP1ADM
L=0.28u
W=4u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N 1280 -30 1280 -70 {}
C {devices/lab_pin.sym} 1280 -70 0 0 {name=l61 lab=VDD}
N 1280 30 1280 70 {}
C {devices/lab_pin.sym} 1280 70 0 0 {name=l62 lab=DM_PREP}
N 1240 0 1180 0 {}
C {devices/lab_pin.sym} 1180 0 0 0 {name=l63 lab=TXOE}
N 1280 0 1340 0 {}
C {devices/lab_pin.sym} 1340 0 0 0 {name=l64 lab=VDD}
C {symbols/pfet_03v3.sym} 1260 0 0 0 {name=MP1BDM
L=0.28u
W=4u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N 1540 -30 1540 -70 {}
C {devices/lab_pin.sym} 1540 -70 0 0 {name=l65 lab=DM_PREP}
N 1540 30 1540 70 {}
C {devices/lab_pin.sym} 1540 70 0 0 {name=l66 lab=DM_NX}
N 1500 0 1440 0 {}
C {devices/lab_pin.sym} 1440 0 0 0 {name=l67 lab=TXDM}
N 1540 0 1600 0 {}
C {devices/lab_pin.sym} 1600 0 0 0 {name=l68 lab=VSS}
C {symbols/nfet_03v3.sym} 1520 0 0 0 {name=MN1ADM
L=0.28u
W=4u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N 1800 -30 1800 -70 {}
C {devices/lab_pin.sym} 1800 -70 0 0 {name=l69 lab=DM_NX}
N 1800 30 1800 70 {}
C {devices/lab_pin.sym} 1800 70 0 0 {name=l70 lab=VSS}
N 1760 0 1700 0 {}
C {devices/lab_pin.sym} 1700 0 0 0 {name=l71 lab=TXOE}
N 1800 0 1860 0 {}
C {devices/lab_pin.sym} 1860 0 0 0 {name=l72 lab=VSS}
C {symbols/nfet_03v3.sym} 1780 0 0 0 {name=MN1BDM
L=0.28u
W=4u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N 2040 -30 2040 -70 {}
C {devices/lab_pin.sym} 2040 -70 0 0 {name=l73 lab=DM_PREP}
N 2040 30 2040 70 {}
C {devices/lab_pin.sym} 2040 70 0 0 {name=l74 lab=DM_GATEP}
N 2020 0 1960 0 {}
C {devices/lab_pin.sym} 1960 0 0 0 {name=l75 lab=VSS}
C {symbols/ppolyf_u.sym} 2040 0 0 0 {name=RSLEWPDM
W=1u
L=2u
model=ppolyf_u
spiceprefix=X
m=1
}
N 1020 270 1020 230 {}
C {devices/lab_pin.sym} 1020 230 0 0 {name=l76 lab=VDD}
N 1020 330 1020 370 {}
C {devices/lab_pin.sym} 1020 370 0 0 {name=l77 lab=DM_PX}
N 980 300 920 300 {}
C {devices/lab_pin.sym} 920 300 0 0 {name=l78 lab=TXDM}
N 1020 300 1080 300 {}
C {devices/lab_pin.sym} 1080 300 0 0 {name=l79 lab=VDD}
C {symbols/pfet_03v3.sym} 1000 300 0 0 {name=MP3ADM
L=0.28u
W=8u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N 1280 270 1280 230 {}
C {devices/lab_pin.sym} 1280 230 0 0 {name=l80 lab=DM_PX}
N 1280 330 1280 370 {}
C {devices/lab_pin.sym} 1280 370 0 0 {name=l81 lab=DM_PREN}
N 1240 300 1180 300 {}
C {devices/lab_pin.sym} 1180 300 0 0 {name=l82 lab=TXOEB}
N 1280 300 1340 300 {}
C {devices/lab_pin.sym} 1340 300 0 0 {name=l83 lab=VDD}
C {symbols/pfet_03v3.sym} 1260 300 0 0 {name=MP3BDM
L=0.28u
W=8u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N 1540 270 1540 230 {}
C {devices/lab_pin.sym} 1540 230 0 0 {name=l84 lab=DM_PREN}
N 1540 330 1540 370 {}
C {devices/lab_pin.sym} 1540 370 0 0 {name=l85 lab=VSS}
N 1500 300 1440 300 {}
C {devices/lab_pin.sym} 1440 300 0 0 {name=l86 lab=TXDM}
N 1540 300 1600 300 {}
C {devices/lab_pin.sym} 1600 300 0 0 {name=l87 lab=VSS}
C {symbols/nfet_03v3.sym} 1520 300 0 0 {name=MN3ADM
L=0.28u
W=2u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N 1800 270 1800 230 {}
C {devices/lab_pin.sym} 1800 230 0 0 {name=l88 lab=DM_PREN}
N 1800 330 1800 370 {}
C {devices/lab_pin.sym} 1800 370 0 0 {name=l89 lab=VSS}
N 1760 300 1700 300 {}
C {devices/lab_pin.sym} 1700 300 0 0 {name=l90 lab=TXOEB}
N 1800 300 1860 300 {}
C {devices/lab_pin.sym} 1860 300 0 0 {name=l91 lab=VSS}
C {symbols/nfet_03v3.sym} 1780 300 0 0 {name=MN3BDM
L=0.28u
W=2u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N 2040 270 2040 230 {}
C {devices/lab_pin.sym} 2040 230 0 0 {name=l92 lab=DM_PREN}
N 2040 330 2040 370 {}
C {devices/lab_pin.sym} 2040 370 0 0 {name=l93 lab=DM_GATEN}
N 2020 300 1960 300 {}
C {devices/lab_pin.sym} 1960 300 0 0 {name=l94 lab=VSS}
C {symbols/ppolyf_u.sym} 2040 300 0 0 {name=RSLEWNDM
W=1u
L=2u
model=ppolyf_u
spiceprefix=X
m=1
}
N 1020 570 1020 530 {}
C {devices/lab_pin.sym} 1020 530 0 0 {name=l95 lab=VDD}
N 1020 630 1020 670 {}
C {devices/lab_pin.sym} 1020 670 0 0 {name=l96 lab=DM_OUTINT}
N 980 600 920 600 {}
C {devices/lab_pin.sym} 920 600 0 0 {name=l97 lab=DM_GATEP}
N 1020 600 1080 600 {}
C {devices/lab_pin.sym} 1080 600 0 0 {name=l98 lab=VDD}
C {symbols/pfet_03v3.sym} 1000 600 0 0 {name=MP2DM
L=0.28u
W=60u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N 1280 570 1280 530 {}
C {devices/lab_pin.sym} 1280 530 0 0 {name=l99 lab=DM_OUTINT}
N 1280 630 1280 670 {}
C {devices/lab_pin.sym} 1280 670 0 0 {name=l100 lab=VSS}
N 1240 600 1180 600 {}
C {devices/lab_pin.sym} 1180 600 0 0 {name=l101 lab=DM_GATEN}
N 1280 600 1340 600 {}
C {devices/lab_pin.sym} 1340 600 0 0 {name=l102 lab=VSS}
C {symbols/nfet_03v3.sym} 1260 600 0 0 {name=MN2DM
L=0.28u
W=30u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N 1520 570 1520 530 {}
C {devices/lab_pin.sym} 1520 530 0 0 {name=l103 lab=DM_OUTINT}
N 1520 630 1520 670 {}
C {devices/lab_pin.sym} 1520 670 0 0 {name=l104 lab=DM}
C {symbols/rm1.sym} 1520 600 0 0 {name=RSERDM
W=2u
L=800u
model=rm1
spiceprefix=X
m=1
}
N -1200 -400 -1160 -400 {}
C {devices/iopin.sym} -1200 -400 0 0 {name=p_vdd lab=VDD}
N -1200 -340 -1160 -340 {}
C {devices/iopin.sym} -1200 -340 0 0 {name=p_vss lab=VSS}
N -1200 -280 -1240 -280 {}
C {devices/ipin.sym} -1200 -280 0 1 {name=p_txdp lab=TXDP}
N -1200 -220 -1240 -220 {}
C {devices/ipin.sym} -1200 -220 0 1 {name=p_txdm lab=TXDM}
N -1200 -160 -1240 -160 {}
C {devices/ipin.sym} -1200 -160 0 1 {name=p_txoe lab=TXOE}
N 1600 -280 1640 -280 {}
C {devices/iopin.sym} 1600 -280 0 0 {name=p_dp lab=DP}
N 1600 -220 1640 -220 {}
C {devices/iopin.sym} 1600 -220 0 0 {name=p_dm lab=DM}
