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
W=4u
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
W=2u
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
C {symbols/pfet_03v3.sym} -180 0 0 0 {name=MP2DP
L=0.28u
W=60u
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
C {symbols/nfet_03v3.sym} 60 0 0 0 {name=MN2DP
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
W=4u
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
W=2u
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
C {symbols/pfet_03v3.sym} 1220 0 0 0 {name=MP2DM
L=0.28u
W=60u
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
C {symbols/nfet_03v3.sym} 1460 0 0 0 {name=MN2DM
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
