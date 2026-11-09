"""
GPS acquisition - decider (Embedded Python Block)

Inputs : the two stock acquisition branches, each a 2048-float vector per 20 ms
         (|correlation|^2 at all 2048 code phases, 20 ms non-coherent sum).
         in0 = Doppler m kHz, in1 = m kHz + 500 Hz. Each vector carries the
         'acq' = (prn, m) tag from the taps scheduler.
Builds the 42-row Doppler x 2048 code-phase grid for one PRN, then decides:
         peak/mean > threshold -> parabolic Doppler refinement -> 'assign' message
         to a free tracking channel.
Messages out: assign (dict), corr / dopp / acq (float PDUs for QT Time Sinks).
Message in  : status (from trackers: 'lost' frees a channel).
A candidate must pass two tests: peak/mean > threshold, and the 20 ms sum must have
averaged at least min_dof independent milliseconds (rejects periodic interference).

Why an EPB: collecting a 2-D grid across time, picking a peak with a decision rule
and handing a timing reference to another block has no stock equivalent.
"""
import time
import numpy as np
from gnuradio import gr
import pmt


class blk(gr.sync_block):
    """GPS acq decider: grid -> peak/mean -> assign a tracking channel"""

    def __init__(self, samp_rate=2.048e6, m_max=10, n_noncoh=20, threshold=3.5, n_ch=4,
                 min_dof=5.0):
        self.N = int(round(samp_rate * 1e-3))
        gr.sync_block.__init__(self, name='GPS acq decider',
                               in_sig=[(np.float32, self.N), (np.float32, self.N)],
                               out_sig=None)
        self.fs = float(samp_rate)
        self.m_max = int(m_max)
        self.K = int(n_noncoh)
        self.thr = float(threshold)
        self.n_ch = int(n_ch)
        self.min_dof = float(min_dof)
        self.t_warn = 0.0
        self.busy = {}                       # ch -> prn
        self.metric = np.zeros(32, np.float32)
        self.cur = None
        self.rows = {}
        for p in ('assign', 'corr', 'dopp', 'acq'):
            self.message_port_register_out(pmt.intern(p))
        self.message_port_register_in(pmt.intern('status'))
        self.set_msg_handler(pmt.intern('status'), self._status)

    def _status(self, msg):
        d = pmt.to_python(msg)
        if isinstance(d, dict) and d.get('event') == 'lost':
            self.busy.pop(int(d['ch']), None)

    def work(self, input_items, output_items):
        a, b = input_items
        base = self.nitems_read(0)
        tags = self.get_tags_in_window(0, 0, len(a), pmt.intern('acq'))
        lab = {t.offset - base: pmt.to_python(t.value) for t in tags}
        for j in range(len(a)):
            if j not in lab:
                continue                      # unlabelled (should not happen)
            prn, m = int(lab[j][0]), int(lab[j][1])
            if prn == 0:
                continue                      # warm-up window
            w = base + j                      # window index: ms [w*K, w*K+K)
            if self.cur is not None and prn != self.cur:
                self.rows = {}                # partial sweep (scheduler skipped ahead)
            self.cur = prn
            s_mid = (w * self.K + self.K // 2) * self.N    # sample at window middle
            # each row normalised by its own mean: immune to slow level changes (AGC)
            self.rows[m * 1000] = (a[j] / max(a[j].mean(), 1e-30), s_mid)
            self.rows[m * 1000 + 500] = (b[j] / max(b[j].mean(), 1e-30), s_mid)
            if m == self.m_max:
                if len(self.rows) == 2 * (2 * self.m_max + 1):
                    self._decide(prn)
                self.rows, self.cur = {}, None
        return len(a)

    def _decide(self, prn):
        freqs = sorted(self.rows)
        G = np.array([self.rows[f][0] for f in freqs])
        mean = G.mean()
        d, tau = np.unravel_index(np.argmax(G), G.shape)
        metric = G[d, tau] / mean
        self.metric[prn - 1] = metric
        f = float(freqs[d])
        if 0 < d < len(freqs) - 1:            # neighbours: best value within +-2 samples
            win = [(tau + k) % self.N for k in range(-2, 3)]
            y0, y1, y2 = G[d - 1, win].max(), G[d, tau], G[d + 1, win].max()
            den = y0 - 2 * y1 + y2
            if den < 0:
                f += 0.5 * (y0 - y2) / den * 500.0
        # second test: did the 20 ms sum really average 20 independent milliseconds?
        # In white noise each cell is a sum of n_noncoh independent |corr|^2 values, so the
        # row (peak excluded) has variance 1/n_noncoh -> effective dof = 1/var ~ 20.
        # Interference that repeats every 1 ms or 125 us (USB / digital noise from the
        # dongle, laptop or bias-tee supply), or a strong CW spur, is IDENTICAL in every
        # millisecond: the sum averages nothing, dof collapses to ~1, and peak/mean reaches
        # ~ln(86000) = 11 for EVERY PRN. Those are rejected here.
        mask = np.ones(self.N, bool)
        mask[[(tau + k) % self.N for k in range(-3, 4)]] = False
        rest = G[d, mask]
        dof = 1.0 / max(np.var(rest / rest.mean()), 1e-9)
        ratio = G[d, tau] / rest.max()
        self._pub('corr', G[d] / mean)
        self._pub('dopp', G[:, tau] / mean)
        self._pub('acq', self.metric)
        if metric < self.thr or prn in self.busy.values():
            return
        if dof < self.min_dof:
            now = time.time()
            if now - self.t_warn > 5.0:
                self.t_warn = now
                print('[INTERFERENCE] PRN %02d peak/mean %.1f rejected: the %d ms sum behaves like '
                      '%.1f independent ms (white noise: ~%d). Something repeats every 1 ms: '
                      'look for a picket fence on the raw spectrum.' % (prn, metric, self.K, dof,
                                                                         self.K), flush=True)
            return
        free = [c for c in range(self.n_ch) if c not in self.busy]
        if not free:
            return
        ch = free[0]
        s_ref = int(self.rows[freqs[d]][1] + tau)   # a code epoch (chip 0) sample index
        self.busy[ch] = prn
        # s_ref goes out as a float: it passes 2^31 after 17.5 min, and pmt.to_pmt() turns a
        # Python int into a C long, which is 32-bit on Windows. A double is exact to 2^53.
        self.message_port_pub(pmt.intern('assign'), pmt.to_pmt(
            {'event': 'assign', 'ch': ch, 'prn': prn, 'f': f, 's_ref': float(s_ref)}))
        print('[ACQ] PRN %02d -> ch%d  Doppler %+7.0f Hz  code epoch at sample %d  '
              'peak/mean %.1f  peak/2nd %.2f  dof %.0f' % (prn, ch, f, s_ref, metric, ratio, dof), flush=True)

    def _pub(self, port, v):
        v = np.asarray(v, np.float32)
        self.message_port_pub(pmt.intern(port),
                              pmt.cons(pmt.PMT_NIL, pmt.init_f32vector(len(v), v.tolist())))
