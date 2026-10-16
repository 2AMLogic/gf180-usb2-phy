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
Output stage per half: PMOS W=80u as 4 parallel m=1 devices, NMOS W=30u as 4 parallel m=1 devices (Wp:Wn = 8:3, wider
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
C {devices/lab_pin.sym} -160 -70 0 0 {name=l12 lab=VDD}
N -200 0 -260 0 {}
C {devices/lab_pin.sym} -260 0 0 0 {name=l13 lab=DP_GATE}
N -160 30 -160 70 {}
C {devices/lab_pin.sym} -160 70 0 0 {name=l14 lab=DP_OUTINT}
N -160 0 -100 0 {}
C {devices/lab_pin.sym} -100 0 0 0 {name=l15 lab=VDD}
C {symbols/pfet_03v3.sym} -180 0 0 0 {name=MP2DP_1
L=0.28u
W=80u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N -160 130 -160 90 {}
C {devices/lab_pin.sym} -160 90 0 0 {name=l43 lab=VDD}
N -200 160 -260 160 {}
C {devices/lab_pin.sym} -260 160 0 0 {name=l44 lab=DP_GATE}
N -160 190 -160 230 {}
C {devices/lab_pin.sym} -160 230 0 0 {name=l45 lab=DP_OUTINT}
N -160 160 -100 160 {}
C {devices/lab_pin.sym} -100 160 0 0 {name=l46 lab=VDD}
C {symbols/pfet_03v3.sym} -180 160 0 0 {name=MP2DP_2
L=0.28u
W=80u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N -160 290 -160 250 {}
C {devices/lab_pin.sym} -160 250 0 0 {name=l47 lab=VDD}
N -200 320 -260 320 {}
C {devices/lab_pin.sym} -260 320 0 0 {name=l48 lab=DP_GATE}
N -160 350 -160 390 {}
C {devices/lab_pin.sym} -160 390 0 0 {name=l49 lab=DP_OUTINT}
N -160 320 -100 320 {}
C {devices/lab_pin.sym} -100 320 0 0 {name=l50 lab=VDD}
C {symbols/pfet_03v3.sym} -180 320 0 0 {name=MP2DP_3
L=0.28u
W=80u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N -160 450 -160 410 {}
C {devices/lab_pin.sym} -160 410 0 0 {name=l51 lab=VDD}
N -200 480 -260 480 {}
C {devices/lab_pin.sym} -260 480 0 0 {name=l52 lab=DP_GATE}
N -160 510 -160 550 {}
C {devices/lab_pin.sym} -160 550 0 0 {name=l53 lab=DP_OUTINT}
N -160 480 -100 480 {}
C {devices/lab_pin.sym} -100 480 0 0 {name=l54 lab=VDD}
C {symbols/pfet_03v3.sym} -180 480 0 0 {name=MP2DP_4
L=0.28u
W=80u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N 80 30 80 70 {}
C {devices/lab_pin.sym} 80 70 0 0 {name=l16 lab=VSS}
N 40 0 -20 0 {}
C {devices/lab_pin.sym} -20 0 0 0 {name=l17 lab=DP_GATE}
N 80 -30 80 -70 {}
C {devices/lab_pin.sym} 80 -70 0 0 {name=l18 lab=DP_OUTINT}
N 80 0 140 0 {}
C {devices/lab_pin.sym} 140 0 0 0 {name=l19 lab=VSS}
C {symbols/nfet_03v3.sym} 60 0 0 0 {name=MN2DP_1
L=0.28u
W=30u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N 80 190 80 230 {}
C {devices/lab_pin.sym} 80 230 0 0 {name=l55 lab=VSS}
N 40 160 -20 160 {}
C {devices/lab_pin.sym} -20 160 0 0 {name=l56 lab=DP_GATE}
N 80 130 80 90 {}
C {devices/lab_pin.sym} 80 90 0 0 {name=l57 lab=DP_OUTINT}
N 80 160 140 160 {}
C {devices/lab_pin.sym} 140 160 0 0 {name=l58 lab=VSS}
C {symbols/nfet_03v3.sym} 60 160 0 0 {name=MN2DP_2
L=0.28u
W=30u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N 80 350 80 390 {}
C {devices/lab_pin.sym} 80 390 0 0 {name=l59 lab=VSS}
N 40 320 -20 320 {}
C {devices/lab_pin.sym} -20 320 0 0 {name=l60 lab=DP_GATE}
N 80 290 80 250 {}
C {devices/lab_pin.sym} 80 250 0 0 {name=l61 lab=DP_OUTINT}
N 80 320 140 320 {}
C {devices/lab_pin.sym} 140 320 0 0 {name=l62 lab=VSS}
C {symbols/nfet_03v3.sym} 60 320 0 0 {name=MN2DP_3
L=0.28u
W=30u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N 80 510 80 550 {}
C {devices/lab_pin.sym} 80 550 0 0 {name=l63 lab=VSS}
N 40 480 -20 480 {}
C {devices/lab_pin.sym} -20 480 0 0 {name=l64 lab=DP_GATE}
N 80 450 80 410 {}
C {devices/lab_pin.sym} 80 410 0 0 {name=l65 lab=DP_OUTINT}
N 80 480 140 480 {}
C {devices/lab_pin.sym} 140 480 0 0 {name=l66 lab=VSS}
C {symbols/nfet_03v3.sym} 60 480 0 0 {name=MN2DP_4
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
C {devices/lab_pin.sym} 1240 -70 0 0 {name=l33 lab=VDD}
N 1200 0 1140 0 {}
C {devices/lab_pin.sym} 1140 0 0 0 {name=l34 lab=DM_GATE}
N 1240 30 1240 70 {}
C {devices/lab_pin.sym} 1240 70 0 0 {name=l35 lab=DM_OUTINT}
N 1240 0 1300 0 {}
C {devices/lab_pin.sym} 1300 0 0 0 {name=l36 lab=VDD}
C {symbols/pfet_03v3.sym} 1220 0 0 0 {name=MP2DM_1
L=0.28u
W=80u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N 1240 130 1240 90 {}
C {devices/lab_pin.sym} 1240 90 0 0 {name=l67 lab=VDD}
N 1200 160 1140 160 {}
C {devices/lab_pin.sym} 1140 160 0 0 {name=l68 lab=DM_GATE}
N 1240 190 1240 230 {}
C {devices/lab_pin.sym} 1240 230 0 0 {name=l69 lab=DM_OUTINT}
N 1240 160 1300 160 {}
C {devices/lab_pin.sym} 1300 160 0 0 {name=l70 lab=VDD}
C {symbols/pfet_03v3.sym} 1220 160 0 0 {name=MP2DM_2
L=0.28u
W=80u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N 1240 290 1240 250 {}
C {devices/lab_pin.sym} 1240 250 0 0 {name=l71 lab=VDD}
N 1200 320 1140 320 {}
C {devices/lab_pin.sym} 1140 320 0 0 {name=l72 lab=DM_GATE}
N 1240 350 1240 390 {}
C {devices/lab_pin.sym} 1240 390 0 0 {name=l73 lab=DM_OUTINT}
N 1240 320 1300 320 {}
C {devices/lab_pin.sym} 1300 320 0 0 {name=l74 lab=VDD}
C {symbols/pfet_03v3.sym} 1220 320 0 0 {name=MP2DM_3
L=0.28u
W=80u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N 1240 450 1240 410 {}
C {devices/lab_pin.sym} 1240 410 0 0 {name=l75 lab=VDD}
N 1200 480 1140 480 {}
C {devices/lab_pin.sym} 1140 480 0 0 {name=l76 lab=DM_GATE}
N 1240 510 1240 550 {}
C {devices/lab_pin.sym} 1240 550 0 0 {name=l77 lab=DM_OUTINT}
N 1240 480 1300 480 {}
C {devices/lab_pin.sym} 1300 480 0 0 {name=l78 lab=VDD}
C {symbols/pfet_03v3.sym} 1220 480 0 0 {name=MP2DM_4
L=0.28u
W=80u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N 1480 30 1480 70 {}
C {devices/lab_pin.sym} 1480 70 0 0 {name=l37 lab=VSS}
N 1440 0 1380 0 {}
C {devices/lab_pin.sym} 1380 0 0 0 {name=l38 lab=DM_GATE}
N 1480 -30 1480 -70 {}
C {devices/lab_pin.sym} 1480 -70 0 0 {name=l39 lab=DM_OUTINT}
N 1480 0 1540 0 {}
C {devices/lab_pin.sym} 1540 0 0 0 {name=l40 lab=VSS}
C {symbols/nfet_03v3.sym} 1460 0 0 0 {name=MN2DM_1
L=0.28u
W=30u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N 1480 190 1480 230 {}
C {devices/lab_pin.sym} 1480 230 0 0 {name=l79 lab=VSS}
N 1440 160 1380 160 {}
C {devices/lab_pin.sym} 1380 160 0 0 {name=l80 lab=DM_GATE}
N 1480 130 1480 90 {}
C {devices/lab_pin.sym} 1480 90 0 0 {name=l81 lab=DM_OUTINT}
N 1480 160 1540 160 {}
C {devices/lab_pin.sym} 1540 160 0 0 {name=l82 lab=VSS}
C {symbols/nfet_03v3.sym} 1460 160 0 0 {name=MN2DM_2
L=0.28u
W=30u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N 1480 350 1480 390 {}
C {devices/lab_pin.sym} 1480 390 0 0 {name=l83 lab=VSS}
N 1440 320 1380 320 {}
C {devices/lab_pin.sym} 1380 320 0 0 {name=l84 lab=DM_GATE}
N 1480 290 1480 250 {}
C {devices/lab_pin.sym} 1480 250 0 0 {name=l85 lab=DM_OUTINT}
N 1480 320 1540 320 {}
C {devices/lab_pin.sym} 1540 320 0 0 {name=l86 lab=VSS}
C {symbols/nfet_03v3.sym} 1460 320 0 0 {name=MN2DM_3
L=0.28u
W=30u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N 1480 510 1480 550 {}
C {devices/lab_pin.sym} 1480 550 0 0 {name=l87 lab=VSS}
N 1440 480 1380 480 {}
C {devices/lab_pin.sym} 1380 480 0 0 {name=l88 lab=DM_GATE}
N 1480 450 1480 410 {}
C {devices/lab_pin.sym} 1480 410 0 0 {name=l89 lab=DM_OUTINT}
N 1480 480 1540 480 {}
C {devices/lab_pin.sym} 1540 480 0 0 {name=l90 lab=VSS}
C {symbols/nfet_03v3.sym} 1460 480 0 0 {name=MN2DM_4
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
