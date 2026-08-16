v {xschem version=3.4.7 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
T {differential_receiver -- USB 2.0 FS differential receiver (spec Sec.4)
Recovers D+/D- differential data (J/K states): a self-biased 5T OTA
(NMOS input pair MN_INA/MN_INB, tail current MTAIL, diode+mirror PMOS
load MP_LOADA/MP_LOADB) compares DP against DM directly, followed by a
2-stage inverter buffer (MP_B1/MN_B1, MP_B2/MN_B2) that squares the
small analog swing at AMPOUT into a rail-to-rail digital RXD output.
RXD tracks DP>DM non-inverting (two buffer inversions cancel): RXD=1
when DP is the more-positive line (J), RXD=0 when DM is (K). NRZI/bit
decode of RXD is out of scope here (out-of-scope serial interface
engine per CLAUDE.md) -- this cell stops at the recovered raw bit.
Design-intent target (NOT yet PVT-simulated -- see #26):
  differential sensitivity |DP-DM| > 200mV, over 0.8-2.5V common-mode
  (spec Sec.4).} -1900 -1000 0 0 0.32 0.32 {}
T {Sizing rationale (first-order, hand calc -- to be confirmed by #26 PVT
sim). Self-bias: RBIAS (ppolyf_u_1k, ~200kohm nominal: rsh=1000+/-200
per libs.tech/ngspice/sm141064.ngspice) sets IBIAS = (VDD-Vgs(MNBIAS))
/RBIAS through diode-connected MNBIAS; MTAIL mirrors 2x (W=8u vs
MNBIAS's W=4u, same L) into the input pair's tail node, so no external
bias reference is needed (consistent with CLAUDE.md's scope discipline
-- no bandgap in scope). Input pair MN_INA/MN_INB sized W=20u/L=0.28u
(min-L for gm, wide for low Vov -- headroom toward the 0.8V common-mode
floor). Load MP_LOADA/MP_LOADB sized 2:1 P:N (W=40u vs input pair's
W=20u, gf180mcu 3.3V mobility ratio -- same convention as the driver's
output stage in differential_driver.sch) for a balanced mirror.
Buffer inv1 (MP_B1/MN_B1, W=8u/4u) and inv2 (MP_B2/MN_B2, W=16u/8u)
follow a 2:1 P:N ratio each stage and roughly double per stage (fanout
scaling) to square AMPOUT's small-signal swing to rail-to-rail RXD
without adding excessive extra delay.
Open PVT items (informal spot-check only; #26 owns verification):
  - Common-mode headroom at the 0.8V floor: tail node sits at
    Vcm-Vgs(MN_INA); MTAIL needs Vds >= its Vov to stay in saturation.
    Not verified across process/temperature here.
  - Common-mode headroom at the 2.5V ceiling: MP_LOADB needs Vsg
    headroom as AMPOUT approaches VDD. Not verified across PVT here.} -1900 -650 0 0 0.28 0.28 {}
N -2000 -400 -1960 -400 {}
C {devices/iopin.sym} -2000 -400 0 0 {name=p_vdd lab=VDD}
N -2000 -340 -1960 -340 {}
C {devices/iopin.sym} -2000 -340 0 0 {name=p_vss lab=VSS}
N -2000 -280 -1960 -280 {}
C {devices/ipin.sym} -2000 -280 0 1 {name=p_dp lab=DP}
N -2000 -220 -1960 -220 {}
C {devices/ipin.sym} -2000 -220 0 1 {name=p_dm lab=DM}
N -1600 -30 -1600 -70 {}
C {devices/lab_pin.sym} -1600 -70 0 0 {name=l1 lab=VDD}
N -1600 30 -1600 70 {}
C {devices/lab_pin.sym} -1600 70 0 0 {name=l2 lab=IBIASN}
N -1620 0 -1680 0 {}
C {devices/lab_pin.sym} -1680 0 0 0 {name=l3 lab=VSS}
C {symbols/ppolyf_u_1k.sym} -1600 0 0 0 {name=RBIAS
W=2u
L=400u
model=ppolyf_u_1k
spiceprefix=X
m=1
}
N -1340 -30 -1340 -70 {}
C {devices/lab_pin.sym} -1340 -70 0 0 {name=l4 lab=IBIASN}
N -1380 0 -1440 0 {}
C {devices/lab_pin.sym} -1440 0 0 0 {name=l5 lab=IBIASN}
N -1340 30 -1340 70 {}
C {devices/lab_pin.sym} -1340 70 0 0 {name=l6 lab=VSS}
N -1340 0 -1280 0 {}
C {devices/lab_pin.sym} -1280 0 0 0 {name=l7 lab=VSS}
C {symbols/nfet_03v3.sym} -1360 0 0 0 {name=MNBIAS
L=0.5u
W=4u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N -1100 -30 -1100 -70 {}
C {devices/lab_pin.sym} -1100 -70 0 0 {name=l8 lab=TAIL}
N -1140 0 -1200 0 {}
C {devices/lab_pin.sym} -1200 0 0 0 {name=l9 lab=IBIASN}
N -1100 30 -1100 70 {}
C {devices/lab_pin.sym} -1100 70 0 0 {name=l10 lab=VSS}
N -1100 0 -1040 0 {}
C {devices/lab_pin.sym} -1040 0 0 0 {name=l11 lab=VSS}
C {symbols/nfet_03v3.sym} -1120 0 0 0 {name=MTAIL
L=0.5u
W=8u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N -860 -30 -860 -70 {}
C {devices/lab_pin.sym} -860 -70 0 0 {name=l12 lab=LOADDIODE}
N -900 0 -960 0 {}
C {devices/lab_pin.sym} -960 0 0 0 {name=l13 lab=DP}
N -860 30 -860 70 {}
C {devices/lab_pin.sym} -860 70 0 0 {name=l14 lab=TAIL}
N -860 0 -800 0 {}
C {devices/lab_pin.sym} -800 0 0 0 {name=l15 lab=VSS}
C {symbols/nfet_03v3.sym} -880 0 0 0 {name=MN_INA
L=0.28u
W=20u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N -620 -30 -620 -70 {}
C {devices/lab_pin.sym} -620 -70 0 0 {name=l16 lab=AMPOUT}
N -660 0 -720 0 {}
C {devices/lab_pin.sym} -720 0 0 0 {name=l17 lab=DM}
N -620 30 -620 70 {}
C {devices/lab_pin.sym} -620 70 0 0 {name=l18 lab=TAIL}
N -620 0 -560 0 {}
C {devices/lab_pin.sym} -560 0 0 0 {name=l19 lab=VSS}
C {symbols/nfet_03v3.sym} -640 0 0 0 {name=MN_INB
L=0.28u
W=20u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N -380 -30 -380 -70 {}
C {devices/lab_pin.sym} -380 -70 0 0 {name=l20 lab=VDD}
N -420 0 -480 0 {}
C {devices/lab_pin.sym} -480 0 0 0 {name=l21 lab=LOADDIODE}
N -380 30 -380 70 {}
C {devices/lab_pin.sym} -380 70 0 0 {name=l22 lab=LOADDIODE}
N -380 0 -320 0 {}
C {devices/lab_pin.sym} -320 0 0 0 {name=l23 lab=VDD}
C {symbols/pfet_03v3.sym} -400 0 0 0 {name=MP_LOADA
L=0.28u
W=40u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N -140 -30 -140 -70 {}
C {devices/lab_pin.sym} -140 -70 0 0 {name=l24 lab=VDD}
N -180 0 -240 0 {}
C {devices/lab_pin.sym} -240 0 0 0 {name=l25 lab=LOADDIODE}
N -140 30 -140 70 {}
C {devices/lab_pin.sym} -140 70 0 0 {name=l26 lab=AMPOUT}
N -140 0 -80 0 {}
C {devices/lab_pin.sym} -80 0 0 0 {name=l27 lab=VDD}
C {symbols/pfet_03v3.sym} -160 0 0 0 {name=MP_LOADB
L=0.28u
W=40u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N 100 -30 100 -70 {}
C {devices/lab_pin.sym} 100 -70 0 0 {name=l28 lab=VDD}
N 60 0 0 0 {}
C {devices/lab_pin.sym} 0 0 0 0 {name=l29 lab=AMPOUT}
N 100 30 100 70 {}
C {devices/lab_pin.sym} 100 70 0 0 {name=l30 lab=BUF1}
N 100 0 160 0 {}
C {devices/lab_pin.sym} 160 0 0 0 {name=l31 lab=VDD}
C {symbols/pfet_03v3.sym} 80 0 0 0 {name=MP_B1
L=0.28u
W=8u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N 340 -30 340 -70 {}
C {devices/lab_pin.sym} 340 -70 0 0 {name=l32 lab=BUF1}
N 300 0 240 0 {}
C {devices/lab_pin.sym} 240 0 0 0 {name=l33 lab=AMPOUT}
N 340 30 340 70 {}
C {devices/lab_pin.sym} 340 70 0 0 {name=l34 lab=VSS}
N 340 0 400 0 {}
C {devices/lab_pin.sym} 400 0 0 0 {name=l35 lab=VSS}
C {symbols/nfet_03v3.sym} 320 0 0 0 {name=MN_B1
L=0.28u
W=4u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N 580 -30 580 -70 {}
C {devices/lab_pin.sym} 580 -70 0 0 {name=l36 lab=VDD}
N 540 0 480 0 {}
C {devices/lab_pin.sym} 480 0 0 0 {name=l37 lab=BUF1}
N 580 30 580 70 {}
C {devices/lab_pin.sym} 580 70 0 0 {name=l38 lab=RXD}
N 580 0 640 0 {}
C {devices/lab_pin.sym} 640 0 0 0 {name=l39 lab=VDD}
C {symbols/pfet_03v3.sym} 560 0 0 0 {name=MP_B2
L=0.28u
W=16u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N 820 -30 820 -70 {}
C {devices/lab_pin.sym} 820 -70 0 0 {name=l40 lab=RXD}
N 780 0 720 0 {}
C {devices/lab_pin.sym} 720 0 0 0 {name=l41 lab=BUF1}
N 820 30 820 70 {}
C {devices/lab_pin.sym} 820 70 0 0 {name=l42 lab=VSS}
N 820 0 880 0 {}
C {devices/lab_pin.sym} 880 0 0 0 {name=l43 lab=VSS}
C {symbols/nfet_03v3.sym} 800 0 0 0 {name=MN_B2
L=0.28u
W=8u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N 1080 -220 1120 -220 {}
C {devices/iopin.sym} 1120 -220 0 0 {name=p_rxd lab=RXD}
