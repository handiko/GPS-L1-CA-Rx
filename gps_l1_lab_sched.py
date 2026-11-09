"""
GPS acquisition - taps scheduler (Embedded Python Block)

Clocked by the raw 2.048 MS/s stream: one output vector per 1 ms (2048 samples).
Output = the replica spectrum conj(FFT(C/A code)) of the PRN under test, circularly
rotated by m bins. With 1 kHz bin spacing (2048-pt FFT at 2.048 MS/s), rotating the
code spectrum by m bins is the same as testing a Doppler of m kHz:
    |IFFT( FFT(x * e^-j2pi m n/N) * C* )| = |IFFT( FFT(x) * roll(C*, m) )|
so the stock Multiply in the acquisition branches does the Doppler search too.
The half-kHz bins come from a second branch pre-mixed by -500 Hz.

The first warmup_ms (default 500 ms) are tagged PRN 0 and ignored, while the AGC
settles. After that, the hypothesis (PRN, m) changes only on 20 ms boundaries (aligned with the stock
Integrate decim=20), and each change is stamped with a stream tag 'acq' = (prn, m).
The tag rides through Multiply, IFFT, Mag^2 and Integrate to the decider, so every
integrated result is labelled exactly: no guessing about buffer latency.

PARK mode (park_prn = 1..32): the scheduler holds PRN park_prn at Doppler park_khz kHz
(and park_khz + 0.5 kHz in the second branch) so the 1 ms and 20 ms probes can be
watched. park_prn = 0 resumes the automatic sweep. No decisions are made while parked.

Why an EPB: no stock block produces a vector sequence that changes on a schedule
and skips PRNs that are already being tracked (message input 'status').
"""
import numpy as np
from gnuradio import gr
import pmt

G2_TAPS = {1: (2, 6), 2: (3, 7), 3: (4, 8), 4: (5, 9), 5: (1, 9), 6: (2, 10),
           7: (1, 8), 8: (2, 9), 9: (3, 10), 10: (2, 3), 11: (3, 4), 12: (5, 6),
           13: (6, 7), 14: (7, 8), 15: (8, 9), 16: (9, 10), 17: (1, 4), 18: (2, 5),
           19: (3, 6), 20: (4, 7), 21: (5, 8), 22: (6, 9), 23: (1, 3), 24: (4, 6),
           25: (5, 7), 26: (6, 8), 27: (7, 9), 28: (8, 10), 29: (1, 6), 30: (2, 7),
           31: (3, 8), 32: (4, 9)}


def ca_code(prn):
    g1, g2 = [1] * 10, [1] * 10
    a, b = G2_TAPS[prn]
    out = np.empty(1023, np.float32)
    for i in range(1023):
        out[i] = 1 - 2 * (g1[9] ^ g2[a - 1] ^ g2[b - 1])
        g1 = [g1[2] ^ g1[9]] + g1[:9]
        g2 = [g2[1] ^ g2[2] ^ g2[5] ^ g2[7] ^ g2[8] ^ g2[9]] + g2[:9]
    return out


class blk(gr.decim_block):
    """GPS acq taps scheduler: conj(FFT(code)) rotated by Doppler, tagged (prn, m)"""

    def __init__(self, samp_rate=2.048e6, m_max=10, n_noncoh=20, warmup_ms=500,
                 park_prn=0, park_khz=0):
        self.N = int(round(samp_rate * 1e-3))
        gr.decim_block.__init__(self, name='GPS acq taps scheduler',
                                in_sig=[np.complex64],
                                out_sig=[(np.complex64, self.N)], decim=self.N)
        self.m_max = int(m_max)
        self.K = int(n_noncoh)
        n = np.arange(self.N)
        idx = np.floor(n * 1.023e6 / samp_rate).astype(int) % 1023
        self.cconj = {p: np.conj(np.fft.fft(ca_code(p)[idx])).astype(np.complex64)
                      for p in range(1, 33)}
        self.ms_list = list(range(-self.m_max, self.m_max + 1))
        self.prn, self.mi = 1, -1
        self.taps = None
        self.tracked = set()
        self.park_prn = int(park_prn)          # GRC callback sets these live
        self.park_khz = int(park_khz)
        self.warm = int(warmup_ms) // self.K * self.K   # whole windows of warm-up
        self.zero = np.zeros(self.N, np.complex64)
        self.set_output_multiple(self.K)          # one call = one 20 ms window
        self.message_port_register_in(pmt.intern('status'))
        self.set_msg_handler(pmt.intern('status'), self._status)

    def _status(self, msg):
        d = pmt.to_python(msg)
        if not isinstance(d, dict):
            return
        if d.get('event') in ('assign', 'assigned'):
            self.tracked.add(int(d['prn']))
        elif d.get('event') == 'lost':
            self.tracked.discard(int(d['prn']))

    def _next(self):
        self.mi += 1
        if self.mi >= len(self.ms_list):
            self.mi = 0
            for _ in range(32):                      # next PRN not being tracked
                self.prn = self.prn % 32 + 1
                if self.prn not in self.tracked or len(self.tracked) >= 32:
                    break
        m = self.ms_list[self.mi]
        self.taps = np.roll(self.cconj[self.prn], m)
        return m

    def work(self, input_items, output_items):
        out = output_items[0]
        base = self.nitems_written(0)
        for j in range(len(out)):
            ms = base + j
            if ms < self.warm:                  # AGC / DC blocker settling: PRN 0 = ignore
                if ms == 0:
                    self.add_item_tag(0, 0, pmt.intern('acq'),
                                      pmt.make_tuple(pmt.from_long(0), pmt.from_long(0)))
                out[j] = self.zero
                continue
            if ms % self.K == 0 and 1 <= int(self.park_prn) <= 32:
                # PARK mode: hold one hypothesis so the probes can be watched
                prn = int(self.park_prn)
                m = int(max(-self.m_max, min(self.m_max, int(self.park_khz))))
                self.taps = np.roll(self.cconj[prn], m)
                self.add_item_tag(0, ms, pmt.intern('acq'),
                                  pmt.make_tuple(pmt.from_long(prn), pmt.from_long(m)))
            elif ms % self.K == 0 or self.taps is None:
                m = self._next()
                self.add_item_tag(0, ms, pmt.intern('acq'),
                                  pmt.make_tuple(pmt.from_long(self.prn), pmt.from_long(m)))
            out[j] = self.taps
        return len(out)
