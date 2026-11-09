"""
GPS navigation message decoder (Embedded Python Block)

Inputs : n_ch byte streams at 50 bit/s, one per tracking channel, from the stock
         gps_nav_bits hier blocks (bit sync -> differential detection -> differential
         encoder -> preamble taggers). Bits are correct up to one overall inversion.
         Stream tags 'preamble' / 'preamble_inv' mark each 10001011 (or 01110100)
         found by the stock Correlate Access Code - Tag blocks.
Message in  'status' : tracker events {'event','ch','prn'} -> reset that channel.
Message out 'text'   : the latest decoded line (for a QT GUI Message Edit Box).

What it does per channel (IS-GPS-200):
  1. Frame sync: a tagged preamble is only a candidate (8 bits occur by chance every
     ~256 bits). It is accepted when TLM and HOW pass the 6-bit parity check, and the
     NEXT subframe, 300 bits later, also passes. Polarity comes from which tag fired.
  2. Every following 300-bit subframe: parity on all 10 words, then decode
     HOW: TOW count (time of week, 6 s units) and subframe ID 1..5
     subframe 1 word 3: 10-bit week number, SV health, URA index, IODC MSBs.
  3. GPS time -> UTC (GPS - 18 s leap seconds; the 10-bit week is unwrapped with
     2 rollovers, valid 2019-04-07 .. 2038-11-20).

Why an EPB: parity checking with the D29*/D30* chaining, frame validation across
subframes and field decoding have no stock GNU Radio equivalent.
"""
import datetime
import numpy as np
from gnuradio import gr
import pmt

PREAMBLE = [1, 0, 0, 0, 1, 0, 1, 1]
LEAP_S = 18
GPS_EPOCH = datetime.datetime(1980, 1, 6)
# parity equations: which data bits (1-based) feed each parity bit, and whether D29* or D30*
PAR = [(29, [1, 2, 3, 5, 6, 10, 11, 12, 13, 14, 17, 18, 20, 23]),
       (30, [2, 3, 4, 6, 7, 11, 12, 13, 14, 15, 18, 19, 21, 24]),
       (29, [1, 3, 4, 5, 7, 8, 12, 13, 14, 15, 16, 19, 20, 22]),
       (30, [2, 4, 5, 6, 8, 9, 13, 14, 15, 16, 17, 20, 21, 23]),
       (30, [1, 3, 5, 6, 7, 9, 10, 14, 15, 16, 17, 18, 21, 22, 24]),
       (29, [3, 5, 6, 8, 9, 10, 11, 13, 15, 19, 22, 23, 24])]


def word_ok(w30, d29s, d30s):
    """w30: 30 transmitted bits. Returns (ok, 24 source data bits)."""
    data = [b ^ d30s for b in w30[:24]]
    star = {29: d29s, 30: d30s}
    for k, (s, idx) in enumerate(PAR):
        p = star[s]
        for i in idx:
            p ^= data[i - 1]
        if p != w30[24 + k]:
            return False, data
    return True, data


def subframe_check(bits, d29s, d30s, n_words=10):
    """bits: 300 transmitted bits (polarity already corrected). Returns list of
    24-bit data words, or None if any parity check fails."""
    words = []
    for w in range(n_words):
        w30 = bits[30 * w:30 * w + 30]
        ok, data = word_ok(w30, d29s, d30s)
        if not ok:
            return None
        words.append(data)
        d29s, d30s = w30[28], w30[29]
    return words


def words_check(bits, d29s, d30s):
    """all 10 words; returns (data words, list of per-word parity results)"""
    words, ok = [], []
    for w in range(10):
        w30 = bits[30 * w:30 * w + 30]
        good, data = word_ok(w30, d29s, d30s)
        words.append(data)
        ok.append(good)
        d29s, d30s = w30[28], w30[29]
    return words, ok


def uint(bits):
    v = 0
    for b in bits:
        v = (v << 1) | int(b)
    return v


def gps_to_utc(week_full, tow_s):
    return GPS_EPOCH + datetime.timedelta(weeks=week_full, seconds=tow_s - LEAP_S)


class blk(gr.sync_block):
    """GPS nav decoder: frame sync, parity, TOW / subframe / week number -> UTC"""

    def __init__(self, n_ch=4):
        self.n = int(n_ch)
        gr.sync_block.__init__(self, name='GPS nav decoder',
                               in_sig=[np.uint8] * self.n, out_sig=None)
        self.message_port_register_in(pmt.intern('status'))
        self.set_msg_handler(pmt.intern('status'), self._status)
        self.message_port_register_out(pmt.intern('text'))
        self.st = [self._fresh(None) for _ in range(self.n)]

    @staticmethod
    def _fresh(prn):
        return dict(prn=prn, buf=[], base=0, cands=[], lock=None, pol=0, week=None,
                    n_ok=0, n_bad=0)

    def _status(self, msg):
        d = pmt.to_python(msg)
        if isinstance(d, dict) and 0 <= int(d.get('ch', -1)) < self.n:
            ch = int(d['ch'])
            self.st[ch] = self._fresh(int(d['prn']) if d.get('event') == 'assigned' else None)

    def _say(self, line):
        print(line, flush=True)
        self.message_port_pub(pmt.intern('text'), pmt.intern(line))

    def work(self, input_items, output_items):
        n = len(input_items[0])
        for c in range(self.n):
            st = self.st[c]
            r0 = self.nitems_read(c)
            if not st['buf']:
                st['base'] = r0
            st['buf'].extend(int(b) & 1 for b in input_items[c])
            for key, pol in (('preamble', 0), ('preamble_inv', 1)):
                for t in self.get_tags_in_window(c, 0, n, pmt.intern(key)):
                    # tag sits on the bit after the 8-bit code -> subframe starts 8 earlier
                    st['cands'].append((t.offset - 8, pol))
            if st['prn'] is not None:
                self._process(c, st)
            else:
                st['cands'] = []
            keep = 900                                # bits kept (3 subframes)
            if len(st['buf']) > keep + 1200:
                drop = len(st['buf']) - keep
                st['buf'] = st['buf'][drop:]
                st['base'] += drop
        return n

    def _get(self, st, start, length):
        i = start - st['base']
        if i < 0 or i + length > len(st['buf']):
            return None
        return st['buf'][i:i + length]

    def _process(self, c, st):
        if st['lock'] is None:                       # frame sync from candidates
            still = []
            for (s, pol) in st['cands']:
                seg = self._get(st, s - 2, 602)       # D29*, D30* + two subframes
                if seg is None:
                    if s - 2 >= st['base']:
                        still.append((s, pol))         # wait for more bits
                    continue
                seg = [b ^ pol for b in seg]
                a = words_check(seg[2:302], seg[0], seg[1])[1]
                b = words_check(seg[302:602], seg[300], seg[301])[1]
                pre2 = seg[302:310] in (PREAMBLE, [x ^ 1 for x in PREAMBLE])
                if a[0] and a[1] and b[0] and b[1] and pre2:
                    st['lock'], st['pol'] = s, pol
                    self._say('[NAV ch%d] PRN %02d frame sync: preamble at bit %d, polarity %s, '
                              'TLM+HOW parity OK on two consecutive subframes' % (
                                  c, st['prn'], s, 'inverted' if pol else 'normal'))
                    break
            else:
                st['cands'] = still
            if st['lock'] is None:
                return
            st['cands'] = []
        while True:                                   # decode every complete subframe
            s = st['lock']
            seg = self._get(st, s - 2, 302)
            if seg is None:
                return
            st['lock'] = s + 300
            # polarity per subframe from its own preamble: differential detection makes
            # every misread transition invert all later bits. GPS parity survives that by
            # design (each word is checked against the previous word's last two RECEIVED
            # bits), so only the word containing the flip is lost.
            if seg[2:10] == PREAMBLE:
                pol = 0
            elif [b ^ 1 for b in seg[2:10]] == PREAMBLE:
                pol = 1
            else:
                pol = None
            words, ok = words_check(seg[2:302], seg[0], seg[1]) if pol is not None else (None, [False] * 10)
            if not (ok[0] and ok[1]):                 # TLM + HOW are the minimum
                st['n_bad'] += 1
                self._say('[NAV ch%d] PRN %02d subframe at bit %d: TLM/HOW parity FAIL (%d in a row)'
                          % (c, st['prn'], s, st['n_bad']))
                if st['n_bad'] >= 3:                  # lost frame sync: search again
                    self._say('[NAV ch%d] PRN %02d frame sync lost, searching' % (c, st['prn']))
                    st['lock'], st['n_bad'] = None, 0
                    return
                continue
            st['n_bad'] = 0
            st['n_ok'] += 1
            self._decode(c, st, words, ok)

    def _decode(self, c, st, w, ok):
        how = w[1]
        tow_next = uint(how[0:17]) * 6               # TOW at start of NEXT subframe
        sfid = uint(how[19:22])
        tow = tow_next - 6                           # TOW at start of THIS subframe
        extra = ''
        bad = [i + 1 for i in range(10) if not ok[i]]
        if bad:
            extra = '  (parity fail in word %s)' % ','.join(map(str, bad))
        if sfid == 1 and ok[2]:
            wn10 = uint(w[2][0:10])
            st['week'] = wn10 + 2048                 # two rollovers (since April 2019)
            ura, health, iodc_msb = uint(w[2][12:16]), uint(w[2][16:22]), uint(w[2][22:24])
            iodc = (iodc_msb << 8) | uint(w[7][0:8]) if ok[7] else -1
            extra += '  week %d (10-bit %d), URA %d, health %s, IODC %d' % (
                st['week'], wn10, ura, 'OK' if health == 0 else '0x%02X' % health, iodc)
        d, rem = divmod(tow, 86400)
        hh, rem = divmod(rem, 3600)
        mm, ss = divmod(rem, 60)
        dow = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'][d % 7]
        line = '[NAV ch%d] PRN %02d subframe %d  TOW %6d s = %s %02d:%02d:%02d GPS%s' % (
            c, st['prn'], sfid, tow, dow, hh, mm, ss, extra)
        if st['week'] is not None:
            line += '  -> UTC %s' % gps_to_utc(st['week'], tow).strftime('%Y-%m-%d %H:%M:%S')
        self._say(line)
