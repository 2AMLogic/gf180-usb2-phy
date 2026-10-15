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
No output-enable/tri-state in this cell -- see design/README.md 'Scope
notes' for why that is deliberately deferred to a PHY-level wrapper.
Design-intent targets (NOT yet PVT-simulated -- see #26):
  rise/fall 10-90% into 50pF: 4-20ns   (Sec.6)
  rise/fall matching: within 10%        (Sec.6)
  crossover voltage: 1.3-2.0V            (Sec.6)
  output resistance: 28-44 ohm           (Sec.6)} -900 -900 0 0 0.35 0.35 {}
T {Sizing rationale (issue #96 re-size; replaces the issue #30 first-order hand calc):
Output stage per half: PMOS W=80u x4 parallel m=1, NMOS W=30u x4 parallel m=1 (Wp:Wn = 8:3, wider
than the 2:1 mobility ratio on purpose: PMOS is the weaker puller, worst
at the fs corner). Large enough that the FETs act as a near-linear Ron
in series with R_series rather than as current-limited sources, which holds
rise/fall matching inside +/-10 % across fs/sf; the old 60/30 stage was
saturation-limited and failed matching at 36/45 corners. Predriver
8u/2.5u (was 4u/2u): its Wp:Wn sets the relative P/N turn-on timing and so
centres the D+/D- crossover inside 1.3-2.0 V.
R_series (rm1, metal1) unchanged: 36 ohm nominal (L/W=400, W=2u L=800u),
rsh_rm1=0.09 +/-0.012 ohm/sq, inside the 28-44 ohm band without a trim.
R_series x 50pF alone is only ~3.4 ns (10-90 %) at the ff corner, below the
4 ns floor, so FET Ron and the R_slew gate RC must supply the rest; the
output stage is therefore deliberately NOT sized any larger. R_slew is
unchanged.
Evidence: sim/driver-signal-quality (record id in design/README.md).} -900 -700 0 0 0.3 0.3 {}
N -880 -30 -880 -70 {}
C {devices/lab_pin.sym} -880 -70 0 0 {name=l1 lab=VDD}
N -920 0 -980 0 {}
C {devices/lab_pin.sym} -980 0 0 0 {name=l2 lab=TXDP}
N -880 30 -880 70 {}
C {devices/lab_pin.sym} -880 70 0 0 {name=l3 lab=DP_PREDRV}
N -880 0 -820 0 {}
C {devices/lab_pin.sym} -820 0 0 0 {name=l4 lab=VDD}
C {symbols/pfet_03v3.sym} -900 0 0 0 {name=MP1DP
L=0.28u
W=8u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N -640 30 -640 70 {}
C {devices/lab_pin.sym} -640 70 0 0 {name=l5 lab=VSS}
N -680 0 -740 0 {}
C {devices/lab_pin.sym} -740 0 0 0 {name=l6 lab=TXDP}
N -640 -30 -640 -70 {}
C {devices/lab_pin.sym} -640 -70 0 0 {name=l7 lab=DP_PREDRV}
N -640 0 -580 0 {}
C {devices/lab_pin.sym} -580 0 0 0 {name=l8 lab=VSS}
C {symbols/nfet_03v3.sym} -660 0 0 0 {name=MN1DP
L=0.28u
W=2.5u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N -420 -30 -420 -70 {}
C {devices/lab_pin.sym} -420 -70 0 0 {name=l9 lab=DP_PREDRV}
N -420 30 -420 70 {}
C {devices/lab_pin.sym} -420 70 0 0 {name=l10 lab=DP_GATE}
N -440 0 -500 0 {}
C {devices/lab_pin.sym} -500 0 0 0 {name=l11 lab=VSS}
C {symbols/ppolyf_u.sym} -420 0 0 0 {name=RSLEWDP
W=1u
L=2u
model=ppolyf_u
spiceprefix=X
m=1
}
N -160 -30 -160 -70 {}
C {devices/lab_pin.sym} -160 -70 0 0 {name=l101 lab=VDD}
N -200 0 -260 0 {}
C {devices/lab_pin.sym} -260 0 0 0 {name=l102 lab=DP_GATE}
N -160 30 -160 70 {}
C {devices/lab_pin.sym} -160 70 0 0 {name=l103 lab=DP_OUTINT}
N -160 0 -100 0 {}
C {devices/lab_pin.sym} -100 0 0 0 {name=l104 lab=VDD}
C {symbols/pfet_03v3.sym} -180 0 0 0 {name=MP2DP_1
L=0.28u
W=80u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N -160 170 -160 130 {}
C {devices/lab_pin.sym} -160 130 0 0 {name=l105 lab=VDD}
N -200 200 -260 200 {}
C {devices/lab_pin.sym} -260 200 0 0 {name=l106 lab=DP_GATE}
N -160 230 -160 270 {}
C {devices/lab_pin.sym} -160 270 0 0 {name=l107 lab=DP_OUTINT}
N -160 200 -100 200 {}
C {devices/lab_pin.sym} -100 200 0 0 {name=l108 lab=VDD}
C {symbols/pfet_03v3.sym} -180 200 0 0 {name=MP2DP_2
L=0.28u
W=80u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N -160 370 -160 330 {}
C {devices/lab_pin.sym} -160 330 0 0 {name=l109 lab=VDD}
N -200 400 -260 400 {}
C {devices/lab_pin.sym} -260 400 0 0 {name=l110 lab=DP_GATE}
N -160 430 -160 470 {}
C {devices/lab_pin.sym} -160 470 0 0 {name=l111 lab=DP_OUTINT}
N -160 400 -100 400 {}
C {devices/lab_pin.sym} -100 400 0 0 {name=l112 lab=VDD}
C {symbols/pfet_03v3.sym} -180 400 0 0 {name=MP2DP_3
L=0.28u
W=80u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N -160 570 -160 530 {}
C {devices/lab_pin.sym} -160 530 0 0 {name=l113 lab=VDD}
N -200 600 -260 600 {}
C {devices/lab_pin.sym} -260 600 0 0 {name=l114 lab=DP_GATE}
N -160 630 -160 670 {}
C {devices/lab_pin.sym} -160 670 0 0 {name=l115 lab=DP_OUTINT}
N -160 600 -100 600 {}
C {devices/lab_pin.sym} -100 600 0 0 {name=l116 lab=VDD}
C {symbols/pfet_03v3.sym} -180 600 0 0 {name=MP2DP_4
L=0.28u
W=80u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N 80 30 80 70 {}
C {devices/lab_pin.sym} 80 70 0 0 {name=l117 lab=VSS}
N 40 0 -20 0 {}
C {devices/lab_pin.sym} -20 0 0 0 {name=l118 lab=DP_GATE}
N 80 -30 80 -70 {}
C {devices/lab_pin.sym} 80 -70 0 0 {name=l119 lab=DP_OUTINT}
N 80 0 140 0 {}
C {devices/lab_pin.sym} 140 0 0 0 {name=l120 lab=VSS}
C {symbols/nfet_03v3.sym} 60 0 0 0 {name=MN2DP_1
L=0.28u
W=30u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N 80 230 80 270 {}
C {devices/lab_pin.sym} 80 270 0 0 {name=l121 lab=VSS}
N 40 200 -20 200 {}
C {devices/lab_pin.sym} -20 200 0 0 {name=l122 lab=DP_GATE}
N 80 170 80 130 {}
C {devices/lab_pin.sym} 80 130 0 0 {name=l123 lab=DP_OUTINT}
N 80 200 140 200 {}
C {devices/lab_pin.sym} 140 200 0 0 {name=l124 lab=VSS}
C {symbols/nfet_03v3.sym} 60 200 0 0 {name=MN2DP_2
L=0.28u
W=30u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N 80 430 80 470 {}
C {devices/lab_pin.sym} 80 470 0 0 {name=l125 lab=VSS}
N 40 400 -20 400 {}
C {devices/lab_pin.sym} -20 400 0 0 {name=l126 lab=DP_GATE}
N 80 370 80 330 {}
C {devices/lab_pin.sym} 80 330 0 0 {name=l127 lab=DP_OUTINT}
N 80 400 140 400 {}
C {devices/lab_pin.sym} 140 400 0 0 {name=l128 lab=VSS}
C {symbols/nfet_03v3.sym} 60 400 0 0 {name=MN2DP_3
L=0.28u
W=30u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N 80 630 80 670 {}
C {devices/lab_pin.sym} 80 670 0 0 {name=l129 lab=VSS}
N 40 600 -20 600 {}
C {devices/lab_pin.sym} -20 600 0 0 {name=l130 lab=DP_GATE}
N 80 570 80 530 {}
C {devices/lab_pin.sym} 80 530 0 0 {name=l131 lab=DP_OUTINT}
N 80 600 140 600 {}
C {devices/lab_pin.sym} 140 600 0 0 {name=l132 lab=VSS}
C {symbols/nfet_03v3.sym} 60 600 0 0 {name=MN2DP_4
L=0.28u
W=30u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N 300 -30 300 -70 {}
C {devices/lab_pin.sym} 300 -70 0 0 {name=l20 lab=DP_OUTINT}
N 300 30 300 70 {}
C {devices/lab_pin.sym} 300 70 0 0 {name=l21 lab=DP}
C {symbols/rm1.sym} 300 0 0 0 {name=RSERDP
W=2u
L=800u
model=rm1
spiceprefix=X
m=1
}
N 520 -30 520 -70 {}
C {devices/lab_pin.sym} 520 -70 0 0 {name=l22 lab=VDD}
N 480 0 420 0 {}
C {devices/lab_pin.sym} 420 0 0 0 {name=l23 lab=TXDM}
N 520 30 520 70 {}
C {devices/lab_pin.sym} 520 70 0 0 {name=l24 lab=DM_PREDRV}
N 520 0 580 0 {}
C {devices/lab_pin.sym} 580 0 0 0 {name=l25 lab=VDD}
C {symbols/pfet_03v3.sym} 500 0 0 0 {name=MP1DM
L=0.28u
W=8u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N 760 30 760 70 {}
C {devices/lab_pin.sym} 760 70 0 0 {name=l26 lab=VSS}
N 720 0 660 0 {}
C {devices/lab_pin.sym} 660 0 0 0 {name=l27 lab=TXDM}
N 760 -30 760 -70 {}
C {devices/lab_pin.sym} 760 -70 0 0 {name=l28 lab=DM_PREDRV}
N 760 0 820 0 {}
C {devices/lab_pin.sym} 820 0 0 0 {name=l29 lab=VSS}
C {symbols/nfet_03v3.sym} 740 0 0 0 {name=MN1DM
L=0.28u
W=2.5u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N 980 -30 980 -70 {}
C {devices/lab_pin.sym} 980 -70 0 0 {name=l30 lab=DM_PREDRV}
N 980 30 980 70 {}
C {devices/lab_pin.sym} 980 70 0 0 {name=l31 lab=DM_GATE}
N 960 0 900 0 {}
C {devices/lab_pin.sym} 900 0 0 0 {name=l32 lab=VSS}
C {symbols/ppolyf_u.sym} 980 0 0 0 {name=RSLEWDM
W=1u
L=2u
model=ppolyf_u
spiceprefix=X
m=1
}
N 1240 -30 1240 -70 {}
C {devices/lab_pin.sym} 1240 -70 0 0 {name=l133 lab=VDD}
N 1200 0 1140 0 {}
C {devices/lab_pin.sym} 1140 0 0 0 {name=l134 lab=DM_GATE}
N 1240 30 1240 70 {}
C {devices/lab_pin.sym} 1240 70 0 0 {name=l135 lab=DM_OUTINT}
N 1240 0 1300 0 {}
C {devices/lab_pin.sym} 1300 0 0 0 {name=l136 lab=VDD}
C {symbols/pfet_03v3.sym} 1220 0 0 0 {name=MP2DM_1
L=0.28u
W=80u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N 1240 170 1240 130 {}
C {devices/lab_pin.sym} 1240 130 0 0 {name=l137 lab=VDD}
N 1200 200 1140 200 {}
C {devices/lab_pin.sym} 1140 200 0 0 {name=l138 lab=DM_GATE}
N 1240 230 1240 270 {}
C {devices/lab_pin.sym} 1240 270 0 0 {name=l139 lab=DM_OUTINT}
N 1240 200 1300 200 {}
C {devices/lab_pin.sym} 1300 200 0 0 {name=l140 lab=VDD}
C {symbols/pfet_03v3.sym} 1220 200 0 0 {name=MP2DM_2
L=0.28u
W=80u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N 1240 370 1240 330 {}
C {devices/lab_pin.sym} 1240 330 0 0 {name=l141 lab=VDD}
N 1200 400 1140 400 {}
C {devices/lab_pin.sym} 1140 400 0 0 {name=l142 lab=DM_GATE}
N 1240 430 1240 470 {}
C {devices/lab_pin.sym} 1240 470 0 0 {name=l143 lab=DM_OUTINT}
N 1240 400 1300 400 {}
C {devices/lab_pin.sym} 1300 400 0 0 {name=l144 lab=VDD}
C {symbols/pfet_03v3.sym} 1220 400 0 0 {name=MP2DM_3
L=0.28u
W=80u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N 1240 570 1240 530 {}
C {devices/lab_pin.sym} 1240 530 0 0 {name=l145 lab=VDD}
N 1200 600 1140 600 {}
C {devices/lab_pin.sym} 1140 600 0 0 {name=l146 lab=DM_GATE}
N 1240 630 1240 670 {}
C {devices/lab_pin.sym} 1240 670 0 0 {name=l147 lab=DM_OUTINT}
N 1240 600 1300 600 {}
C {devices/lab_pin.sym} 1300 600 0 0 {name=l148 lab=VDD}
C {symbols/pfet_03v3.sym} 1220 600 0 0 {name=MP2DM_4
L=0.28u
W=80u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N 1480 30 1480 70 {}
C {devices/lab_pin.sym} 1480 70 0 0 {name=l149 lab=VSS}
N 1440 0 1380 0 {}
C {devices/lab_pin.sym} 1380 0 0 0 {name=l150 lab=DM_GATE}
N 1480 -30 1480 -70 {}
C {devices/lab_pin.sym} 1480 -70 0 0 {name=l151 lab=DM_OUTINT}
N 1480 0 1540 0 {}
C {devices/lab_pin.sym} 1540 0 0 0 {name=l152 lab=VSS}
C {symbols/nfet_03v3.sym} 1460 0 0 0 {name=MN2DM_1
L=0.28u
W=30u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N 1480 230 1480 270 {}
C {devices/lab_pin.sym} 1480 270 0 0 {name=l153 lab=VSS}
N 1440 200 1380 200 {}
C {devices/lab_pin.sym} 1380 200 0 0 {name=l154 lab=DM_GATE}
N 1480 170 1480 130 {}
C {devices/lab_pin.sym} 1480 130 0 0 {name=l155 lab=DM_OUTINT}
N 1480 200 1540 200 {}
C {devices/lab_pin.sym} 1540 200 0 0 {name=l156 lab=VSS}
C {symbols/nfet_03v3.sym} 1460 200 0 0 {name=MN2DM_2
L=0.28u
W=30u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N 1480 430 1480 470 {}
C {devices/lab_pin.sym} 1480 470 0 0 {name=l157 lab=VSS}
N 1440 400 1380 400 {}
C {devices/lab_pin.sym} 1380 400 0 0 {name=l158 lab=DM_GATE}
N 1480 370 1480 330 {}
C {devices/lab_pin.sym} 1480 330 0 0 {name=l159 lab=DM_OUTINT}
N 1480 400 1540 400 {}
C {devices/lab_pin.sym} 1540 400 0 0 {name=l160 lab=VSS}
C {symbols/nfet_03v3.sym} 1460 400 0 0 {name=MN2DM_3
L=0.28u
W=30u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N 1480 630 1480 670 {}
C {devices/lab_pin.sym} 1480 670 0 0 {name=l161 lab=VSS}
N 1440 600 1380 600 {}
C {devices/lab_pin.sym} 1380 600 0 0 {name=l162 lab=DM_GATE}
N 1480 570 1480 530 {}
C {devices/lab_pin.sym} 1480 530 0 0 {name=l163 lab=DM_OUTINT}
N 1480 600 1540 600 {}
C {devices/lab_pin.sym} 1540 600 0 0 {name=l164 lab=VSS}
C {symbols/nfet_03v3.sym} 1460 600 0 0 {name=MN2DM_4
L=0.28u
W=30u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N 1700 -30 1700 -70 {}
C {devices/lab_pin.sym} 1700 -70 0 0 {name=l41 lab=DM_OUTINT}
N 1700 30 1700 70 {}
C {devices/lab_pin.sym} 1700 70 0 0 {name=l42 lab=DM}
C {symbols/rm1.sym} 1700 0 0 0 {name=RSERDM
W=2u
L=800u
model=rm1
spiceprefix=X
m=1
}
N -1200 -400 -1160 -400 {lab=VDD}
C {devices/iopin.sym} -1200 -400 0 0 {name=p_vdd lab=VDD}
N -1200 -340 -1160 -340 {lab=VSS}
C {devices/iopin.sym} -1200 -340 0 0 {name=p_vss lab=VSS}
N -1200 -280 -1240 -280 {lab=TXDP}
C {devices/ipin.sym} -1200 -280 0 1 {name=p_txdp lab=TXDP}
N -1200 -220 -1240 -220 {lab=TXDM}
C {devices/ipin.sym} -1200 -220 0 1 {name=p_txdm lab=TXDM}
N 1600 -280 1640 -280 {lab=DP}
C {devices/iopin.sym} 1600 -280 0 0 {name=p_dp lab=DP}
N 1600 -220 1640 -220 {lab=DM}
C {devices/iopin.sym} 1600 -220 0 0 {name=p_dm lab=DM}
