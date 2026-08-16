v {xschem version=3.4.7 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
T {se_receiver_dp -- USB 2.0 FS single-ended receiver on DP (spec Sec.4)
Comparator-style single-ended receiver: a resistor divider (R1/R2 off
VDD) sets VREF at the midpoint of the VIH/VIL band, (VIH+VIL)/2 =
(2.0+0.8)/2 = 1.4V, so a zero-offset comparator has 0.6V of margin on
each side to satisfy both thresholds. A self-biased 5T OTA (NMOS input
pair MN_INA/MN_INB, tail current MTAIL, diode+mirror PMOS load
MP_LOADA/MP_LOADB) compares DP against VREF, followed by a 2-stage
inverter buffer that squares the small analog swing at AMPOUT into a
rail-to-rail digital RXDP output: RXDP=1 when DP > ~VREF.
Downstream SE0/idle/reset line-state decode (combining RXDP+RXDM) is
out-of-scope digital RTL (tracked separately) -- this cell stops at the
per-line recovered raw bit.
Design-intent target (NOT yet PVT-simulated -- see #26):
  VIH > 2.0V, VIL < 0.8V on DP (spec Sec.4).} -1900 -1000 0 0 0.32 0.32 {}
T {Sizing rationale (first-order, hand calc -- to be confirmed by #26 PVT
sim). R1/R2 (ppolyf_u_1k, rsh=1000+/-200 per
libs.tech/ngspice/sm141064.ngspice): R1=1900ohm (W=2u,L=3.8u),
R2=1400ohm (W=2u,L=2.8u); R1+R2=3300ohm so VREF=VDD*R2/(R1+R2)=
3.3V*1400/3300=1.4V at nominal VDD -- exactly the VIH/VIL midpoint by
construction. This is a supply-referenced (ratiometric) threshold, not
an absolute one: it tracks VDD, which is fine for this cell's purpose
(recognizing rail-referenced J/K/SE0 levels) but is a design choice
worth flagging, not a claim it is immune to VDD variation -- #26's job.
Bias/OTA/buffer sizing (RBIAS ~200kohm self-bias, 2x tail mirror,
W=20u/L=0.28u input pair, 2:1 P:N load and buffer ratios) is identical
to differential_receiver.sch's rationale -- see that schematic's
sizing note for the full argument; not repeated here to avoid drift
between two independently-editable copies (each cell is a flat leaf
per design/netlist.py's module docstring, so some duplication across
the two SE cells and the differential cell is expected).
Open PVT item (informal spot-check only; #26 owns verification):
  comparator input-referred offset (device mismatch, not modelled by
  a first-order hand calc) eats directly into the 0.6V margin on each
  side -- #26's PVT/mismatch sweep is what turns this margin argument
  into a verified claim.} -1900 -650 0 0 0.28 0.28 {}
N -2000 -400 -1960 -400 {}
C {devices/iopin.sym} -2000 -400 0 0 {name=p_vdd lab=VDD}
N -2000 -340 -1960 -340 {}
C {devices/iopin.sym} -2000 -340 0 0 {name=p_vss lab=VSS}
N -2000 -280 -1960 -280 {}
C {devices/ipin.sym} -2000 -280 0 1 {name=p_in lab=DP}
N -1800 -30 -1800 -70 {}
C {devices/lab_pin.sym} -1800 -70 0 0 {name=l1 lab=VDD}
N -1800 30 -1800 70 {}
C {devices/lab_pin.sym} -1800 70 0 0 {name=l2 lab=VREF}
N -1820 0 -1880 0 {}
C {devices/lab_pin.sym} -1880 0 0 0 {name=l3 lab=VSS}
C {symbols/ppolyf_u_1k.sym} -1800 0 0 0 {name=R1
W=2u
L=3.8u
model=ppolyf_u_1k
spiceprefix=X
m=1
}
N -1560 -30 -1560 -70 {}
C {devices/lab_pin.sym} -1560 -70 0 0 {name=l4 lab=VREF}
N -1560 30 -1560 70 {}
C {devices/lab_pin.sym} -1560 70 0 0 {name=l5 lab=VSS}
N -1580 0 -1640 0 {}
C {devices/lab_pin.sym} -1640 0 0 0 {name=l6 lab=VSS}
C {symbols/ppolyf_u_1k.sym} -1560 0 0 0 {name=R2
W=2u
L=2.8u
model=ppolyf_u_1k
spiceprefix=X
m=1
}
N -1320 -30 -1320 -70 {}
C {devices/lab_pin.sym} -1320 -70 0 0 {name=l7 lab=VDD}
N -1320 30 -1320 70 {}
C {devices/lab_pin.sym} -1320 70 0 0 {name=l8 lab=IBIASN}
N -1340 0 -1400 0 {}
C {devices/lab_pin.sym} -1400 0 0 0 {name=l9 lab=VSS}
C {symbols/ppolyf_u_1k.sym} -1320 0 0 0 {name=RBIAS
W=2u
L=400u
model=ppolyf_u_1k
spiceprefix=X
m=1
}
N -1060 -30 -1060 -70 {}
C {devices/lab_pin.sym} -1060 -70 0 0 {name=l10 lab=IBIASN}
N -1100 0 -1160 0 {}
C {devices/lab_pin.sym} -1160 0 0 0 {name=l11 lab=IBIASN}
N -1060 30 -1060 70 {}
C {devices/lab_pin.sym} -1060 70 0 0 {name=l12 lab=VSS}
N -1060 0 -1000 0 {}
C {devices/lab_pin.sym} -1000 0 0 0 {name=l13 lab=VSS}
C {symbols/nfet_03v3.sym} -1080 0 0 0 {name=MNBIAS
L=0.5u
W=4u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N -820 -30 -820 -70 {}
C {devices/lab_pin.sym} -820 -70 0 0 {name=l14 lab=TAIL}
N -860 0 -920 0 {}
C {devices/lab_pin.sym} -920 0 0 0 {name=l15 lab=IBIASN}
N -820 30 -820 70 {}
C {devices/lab_pin.sym} -820 70 0 0 {name=l16 lab=VSS}
N -820 0 -760 0 {}
C {devices/lab_pin.sym} -760 0 0 0 {name=l17 lab=VSS}
C {symbols/nfet_03v3.sym} -840 0 0 0 {name=MTAIL
L=0.5u
W=8u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N -580 -30 -580 -70 {}
C {devices/lab_pin.sym} -580 -70 0 0 {name=l18 lab=LOADDIODE}
N -620 0 -680 0 {}
C {devices/lab_pin.sym} -680 0 0 0 {name=l19 lab=DP}
N -580 30 -580 70 {}
C {devices/lab_pin.sym} -580 70 0 0 {name=l20 lab=TAIL}
N -580 0 -520 0 {}
C {devices/lab_pin.sym} -520 0 0 0 {name=l21 lab=VSS}
C {symbols/nfet_03v3.sym} -600 0 0 0 {name=MN_INA
L=0.28u
W=20u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N -340 -30 -340 -70 {}
C {devices/lab_pin.sym} -340 -70 0 0 {name=l22 lab=AMPOUT}
N -380 0 -440 0 {}
C {devices/lab_pin.sym} -440 0 0 0 {name=l23 lab=VREF}
N -340 30 -340 70 {}
C {devices/lab_pin.sym} -340 70 0 0 {name=l24 lab=TAIL}
N -340 0 -280 0 {}
C {devices/lab_pin.sym} -280 0 0 0 {name=l25 lab=VSS}
C {symbols/nfet_03v3.sym} -360 0 0 0 {name=MN_INB
L=0.28u
W=20u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N -100 -30 -100 -70 {}
C {devices/lab_pin.sym} -100 -70 0 0 {name=l26 lab=VDD}
N -140 0 -200 0 {}
C {devices/lab_pin.sym} -200 0 0 0 {name=l27 lab=LOADDIODE}
N -100 30 -100 70 {}
C {devices/lab_pin.sym} -100 70 0 0 {name=l28 lab=LOADDIODE}
N -100 0 -40 0 {}
C {devices/lab_pin.sym} -40 0 0 0 {name=l29 lab=VDD}
C {symbols/pfet_03v3.sym} -120 0 0 0 {name=MP_LOADA
L=0.28u
W=40u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N 140 -30 140 -70 {}
C {devices/lab_pin.sym} 140 -70 0 0 {name=l30 lab=VDD}
N 100 0 40 0 {}
C {devices/lab_pin.sym} 40 0 0 0 {name=l31 lab=LOADDIODE}
N 140 30 140 70 {}
C {devices/lab_pin.sym} 140 70 0 0 {name=l32 lab=AMPOUT}
N 140 0 200 0 {}
C {devices/lab_pin.sym} 200 0 0 0 {name=l33 lab=VDD}
C {symbols/pfet_03v3.sym} 120 0 0 0 {name=MP_LOADB
L=0.28u
W=40u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N 380 -30 380 -70 {}
C {devices/lab_pin.sym} 380 -70 0 0 {name=l34 lab=VDD}
N 340 0 280 0 {}
C {devices/lab_pin.sym} 280 0 0 0 {name=l35 lab=AMPOUT}
N 380 30 380 70 {}
C {devices/lab_pin.sym} 380 70 0 0 {name=l36 lab=BUF1}
N 380 0 440 0 {}
C {devices/lab_pin.sym} 440 0 0 0 {name=l37 lab=VDD}
C {symbols/pfet_03v3.sym} 360 0 0 0 {name=MP_B1
L=0.28u
W=8u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N 620 -30 620 -70 {}
C {devices/lab_pin.sym} 620 -70 0 0 {name=l38 lab=BUF1}
N 580 0 520 0 {}
C {devices/lab_pin.sym} 520 0 0 0 {name=l39 lab=AMPOUT}
N 620 30 620 70 {}
C {devices/lab_pin.sym} 620 70 0 0 {name=l40 lab=VSS}
N 620 0 680 0 {}
C {devices/lab_pin.sym} 680 0 0 0 {name=l41 lab=VSS}
C {symbols/nfet_03v3.sym} 600 0 0 0 {name=MN_B1
L=0.28u
W=4u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N 860 -30 860 -70 {}
C {devices/lab_pin.sym} 860 -70 0 0 {name=l42 lab=VDD}
N 820 0 760 0 {}
C {devices/lab_pin.sym} 760 0 0 0 {name=l43 lab=BUF1}
N 860 30 860 70 {}
C {devices/lab_pin.sym} 860 70 0 0 {name=l44 lab=RXDP}
N 860 0 920 0 {}
C {devices/lab_pin.sym} 920 0 0 0 {name=l45 lab=VDD}
C {symbols/pfet_03v3.sym} 840 0 0 0 {name=MP_B2
L=0.28u
W=16u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N 1100 -30 1100 -70 {}
C {devices/lab_pin.sym} 1100 -70 0 0 {name=l46 lab=RXDP}
N 1060 0 1000 0 {}
C {devices/lab_pin.sym} 1000 0 0 0 {name=l47 lab=BUF1}
N 1100 30 1100 70 {}
C {devices/lab_pin.sym} 1100 70 0 0 {name=l48 lab=VSS}
N 1100 0 1160 0 {}
C {devices/lab_pin.sym} 1160 0 0 0 {name=l49 lab=VSS}
C {symbols/nfet_03v3.sym} 1080 0 0 0 {name=MN_B2
L=0.28u
W=8u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N 1360 -220 1400 -220 {}
C {devices/iopin.sym} 1400 -220 0 0 {name=p_out lab=RXDP}
