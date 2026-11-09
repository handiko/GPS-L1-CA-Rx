#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: GPS L1 C/A lab: acquisition and tracking, every stage probed
# Description: Lab version of gps_l1_despread: stock acquisition branches + 3 EPBs + 3 hier blocks
# GNU Radio version: 3.10.10.0

from PyQt5 import Qt
from gnuradio import qtgui
import os
import sys
sys.path.append(os.environ.get('GRC_HIER_PATH', os.path.expanduser('~/.grc_gnuradio')))

from PyQt5 import QtCore
from gnuradio import analog
from gnuradio import blocks
import pmt
from gnuradio import eng_notation
from gnuradio import filter
from gnuradio.filter import firdes
from gnuradio import gr
from gnuradio.fft import window
import signal
from PyQt5 import Qt
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gps_acq_branch import gps_acq_branch  # grc-generated hier_block
from gps_nav_bits import gps_nav_bits  # grc-generated hier_block
from gps_track_channel import gps_track_channel  # grc-generated hier_block
import gps_l1_lab_decider as decider  # embedded python block
import gps_l1_lab_navdec as navdec  # embedded python block
import gps_l1_lab_sched as sched  # embedded python block
import json
import sip



class gps_l1_lab(gr.top_block, Qt.QWidget):

    def __init__(self):
        gr.top_block.__init__(self, "GPS L1 C/A lab: acquisition and tracking, every stage probed", catch_exceptions=True)
        Qt.QWidget.__init__(self)
        self.setWindowTitle("GPS L1 C/A lab: acquisition and tracking, every stage probed")
        qtgui.util.check_set_qss()
        try:
            self.setWindowIcon(Qt.QIcon.fromTheme('gnuradio-grc'))
        except BaseException as exc:
            print(f"Qt GUI: Could not set Icon: {str(exc)}", file=sys.stderr)
        self.top_scroll_layout = Qt.QVBoxLayout()
        self.setLayout(self.top_scroll_layout)
        self.top_scroll = Qt.QScrollArea()
        self.top_scroll.setFrameStyle(Qt.QFrame.NoFrame)
        self.top_scroll_layout.addWidget(self.top_scroll)
        self.top_scroll.setWidgetResizable(True)
        self.top_widget = Qt.QWidget()
        self.top_scroll.setWidget(self.top_widget)
        self.top_layout = Qt.QVBoxLayout(self.top_widget)
        self.top_grid_layout = Qt.QGridLayout()
        self.top_layout.addLayout(self.top_grid_layout)

        self.settings = Qt.QSettings("GNU Radio", "gps_l1_lab")

        try:
            geometry = self.settings.value("geometry")
            if geometry:
                self.restoreGeometry(geometry)
        except BaseException as exc:
            print(f"Qt GUI: Could not restore geometry: {str(exc)}", file=sys.stderr)

        ##################################################
        # Variables
        ##################################################
        self.base_path = base_path = "C:/Users/Handiko/Downloads/GPS-L1-2022-03-27"
        self.samp_rate = samp_rate = 2.048e6
        self.meta = meta = json.load(open(base_path + '.sigmf-meta'))
        self.decim = decim = 32
        self.threshold = threshold = 3.5
        self.rf_gain = rf_gain = 40.2
        self.ppm = ppm = 0
        self.park_prn = park_prn = 0
        self.park_khz = park_khz = 0
        self.n_noncoh = n_noncoh = 20
        self.m_max = m_max = 10
        self.lpf_taps = lpf_taps = firdes.low_pass(1.0, samp_rate, 22e3, 16e3)
        self.file_samp_rate = file_samp_rate = float(meta['global']['core:sample_rate'])
        self.disp_rate = disp_rate = samp_rate/decim
        self.datatype = datatype = meta['global']['core:datatype']
        self.chips_per_sample = chips_per_sample = 1.023e6/samp_rate
        self.center_freq_0 = center_freq_0 = float(meta['captures'][0].get('core:frequency', 0))
        self.center_freq = center_freq = 1575.42e6
        self.N = N = int(round(samp_rate*1e-3))

        ##################################################
        # Blocks
        ##################################################

        self.tabs = Qt.QTabWidget()
        self.tabs_widget_0 = Qt.QWidget()
        self.tabs_layout_0 = Qt.QBoxLayout(Qt.QBoxLayout.TopToBottom, self.tabs_widget_0)
        self.tabs_grid_layout_0 = Qt.QGridLayout()
        self.tabs_layout_0.addLayout(self.tabs_grid_layout_0)
        self.tabs.addTab(self.tabs_widget_0, 'Spectrum (despread)')
        self.tabs_widget_1 = Qt.QWidget()
        self.tabs_layout_1 = Qt.QBoxLayout(Qt.QBoxLayout.TopToBottom, self.tabs_widget_1)
        self.tabs_grid_layout_1 = Qt.QGridLayout()
        self.tabs_layout_1.addLayout(self.tabs_grid_layout_1)
        self.tabs.addTab(self.tabs_widget_1, 'Acquisition (search)')
        self.tabs_widget_2 = Qt.QWidget()
        self.tabs_layout_2 = Qt.QBoxLayout(Qt.QBoxLayout.TopToBottom, self.tabs_widget_2)
        self.tabs_grid_layout_2 = Qt.QGridLayout()
        self.tabs_layout_2.addLayout(self.tabs_grid_layout_2)
        self.tabs.addTab(self.tabs_widget_2, 'Tracking (loop internals)')
        self.tabs_widget_3 = Qt.QWidget()
        self.tabs_layout_3 = Qt.QBoxLayout(Qt.QBoxLayout.TopToBottom, self.tabs_widget_3)
        self.tabs_grid_layout_3 = Qt.QGridLayout()
        self.tabs_layout_3.addLayout(self.tabs_grid_layout_3)
        self.tabs.addTab(self.tabs_widget_3, 'Navigation data')
        self.top_grid_layout.addWidget(self.tabs, 1, 0, 1, 4)
        for r in range(1, 2):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 4):
            self.top_grid_layout.setColumnStretch(c, 1)
        self._park_prn_range = qtgui.Range(0, 32, 1, 0, 200)
        self._park_prn_win = qtgui.RangeWidget(self._park_prn_range, self.set_park_prn, "Park search on PRN (0 = auto)", "counter_slider", int, QtCore.Qt.Horizontal)
        self.top_grid_layout.addWidget(self._park_prn_win, 0, 2, 1, 1)
        for r in range(0, 1):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(2, 3):
            self.top_grid_layout.setColumnStretch(c, 1)
        self._park_khz_range = qtgui.Range((-m_max), m_max, 1, 0, 200)
        self._park_khz_win = qtgui.RangeWidget(self._park_khz_range, self.set_park_khz, "Park Doppler [kHz]", "counter_slider", int, QtCore.Qt.Horizontal)
        self.top_grid_layout.addWidget(self._park_khz_win, 0, 3, 1, 1)
        for r in range(0, 1):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(3, 4):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.wf_raw = qtgui.waterfall_sink_c(
            512, #size
            window.WIN_BLACKMAN_hARRIS, #wintype
            0, #fc
            disp_rate, #bw
            "Waterfall: raw input (nothing to see)", #name
            1, #number of inputs
            None # parent
        )
        self.wf_raw.set_update_time(0.05)
        self.wf_raw.enable_grid(False)
        self.wf_raw.enable_axis_labels(True)

        self.wf_raw.disable_legend()


        labels = ['', '', '', '', '',
                  '', '', '', '', '']
        colors = [0, 0, 0, 0, 0,
                  0, 0, 0, 0, 0]
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
                  1.0, 1.0, 1.0, 1.0, 1.0]

        for i in range(1):
            if len(labels[i]) == 0:
                self.wf_raw.set_line_label(i, "Data {0}".format(i))
            else:
                self.wf_raw.set_line_label(i, labels[i])
            self.wf_raw.set_color_map(i, colors[i])
            self.wf_raw.set_line_alpha(i, alphas[i])

        self.wf_raw.set_intensity_range(-50, -28)

        self._wf_raw_win = sip.wrapinstance(self.wf_raw.qwidget(), Qt.QWidget)

        self.tabs_grid_layout_0.addWidget(self._wf_raw_win, 1, 0, 1, 1)
        for r in range(1, 2):
            self.tabs_grid_layout_0.setRowStretch(r, 1)
        for c in range(0, 1):
            self.tabs_grid_layout_0.setColumnStretch(c, 1)
        self.wf_c0 = qtgui.waterfall_sink_c(
            512, #size
            window.WIN_BLACKMAN_hARRIS, #wintype
            0, #fc
            disp_rate, #bw
            "Waterfall: channel 0 (line appears at lock)", #name
            1, #number of inputs
            None # parent
        )
        self.wf_c0.set_update_time(0.05)
        self.wf_c0.enable_grid(False)
        self.wf_c0.enable_axis_labels(True)

        self.wf_c0.disable_legend()


        labels = ['', '', '', '', '',
                  '', '', '', '', '']
        colors = [0, 0, 0, 0, 0,
                  0, 0, 0, 0, 0]
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
                  1.0, 1.0, 1.0, 1.0, 1.0]

        for i in range(1):
            if len(labels[i]) == 0:
                self.wf_c0.set_line_label(i, "Data {0}".format(i))
            else:
                self.wf_c0.set_line_label(i, labels[i])
            self.wf_c0.set_color_map(i, colors[i])
            self.wf_c0.set_line_alpha(i, alphas[i])

        self.wf_c0.set_intensity_range(-50, -28)

        self._wf_c0_win = sip.wrapinstance(self.wf_c0.qwidget(), Qt.QWidget)

        self.tabs_grid_layout_0.addWidget(self._wf_c0_win, 1, 1, 1, 1)
        for r in range(1, 2):
            self.tabs_grid_layout_0.setRowStretch(r, 1)
        for c in range(1, 2):
            self.tabs_grid_layout_0.setColumnStretch(c, 1)
        self.vs_bitsync = qtgui.vector_sink_f(
            20,
            0,
            1,
            "start offset",
            "energy",
            "Bit sync: energy of a 20 ms sum vs its start offset (peak = bit edge), per channel",
            4, # Number of inputs
            None # parent
        )
        self.vs_bitsync.set_update_time(0.20)
        self.vs_bitsync.set_y_axis(55, 80)
        self.vs_bitsync.enable_autoscale(False)
        self.vs_bitsync.enable_grid(True)
        self.vs_bitsync.set_x_axis_units("ms")
        self.vs_bitsync.set_y_axis_units("dB")
        self.vs_bitsync.set_ref_level(0)


        labels = ["Ch 0", "Ch 1", "Ch 2", "Ch 3", '',
            '', '', '', '', '']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ["blue", "red", "green", "black", "cyan",
            "magenta", "yellow", "dark red", "dark green", "dark blue"]
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]

        for i in range(4):
            if len(labels[i]) == 0:
                self.vs_bitsync.set_line_label(i, "Data {0}".format(i))
            else:
                self.vs_bitsync.set_line_label(i, labels[i])
            self.vs_bitsync.set_line_width(i, widths[i])
            self.vs_bitsync.set_line_color(i, colors[i])
            self.vs_bitsync.set_line_alpha(i, alphas[i])

        self._vs_bitsync_win = sip.wrapinstance(self.vs_bitsync.qwidget(), Qt.QWidget)
        self.tabs_grid_layout_3.addWidget(self._vs_bitsync_win, 1, 0, 2, 1)
        for r in range(1, 3):
            self.tabs_grid_layout_3.setRowStretch(r, 1)
        for c in range(0, 1):
            self.tabs_grid_layout_3.setColumnStretch(c, 1)
        self.vs_20ms = qtgui.vector_sink_f(
            N,
            0,
            chips_per_sample,
            "code phase",
            "peak/mean",
            "Probe: 20 ms sums, both branches (current PRN / Doppler under test)",
            2, # Number of inputs
            None # parent
        )
        self.vs_20ms.set_update_time(0.05)
        self.vs_20ms.set_y_axis(0, 40)
        self.vs_20ms.enable_autoscale(False)
        self.vs_20ms.enable_grid(True)
        self.vs_20ms.set_x_axis_units("chips")
        self.vs_20ms.set_y_axis_units("")
        self.vs_20ms.set_ref_level(0)


        labels = ["m kHz", "m kHz + 500 Hz", '', '', '',
            '', '', '', '', '']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ["blue", "red", "green", "black", "cyan",
            "magenta", "yellow", "dark red", "dark green", "dark blue"]
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]

        for i in range(2):
            if len(labels[i]) == 0:
                self.vs_20ms.set_line_label(i, "Data {0}".format(i))
            else:
                self.vs_20ms.set_line_label(i, labels[i])
            self.vs_20ms.set_line_width(i, widths[i])
            self.vs_20ms.set_line_color(i, colors[i])
            self.vs_20ms.set_line_alpha(i, alphas[i])

        self._vs_20ms_win = sip.wrapinstance(self.vs_20ms.qwidget(), Qt.QWidget)
        self.tabs_grid_layout_1.addWidget(self._vs_20ms_win, 0, 1, 1, 1)
        for r in range(0, 1):
            self.tabs_grid_layout_1.setRowStretch(r, 1)
        for c in range(1, 2):
            self.tabs_grid_layout_1.setColumnStretch(c, 1)
        self.vs_1ms = qtgui.vector_sink_f(
            N,
            0,
            chips_per_sample,
            "code phase",
            "peak/mean",
            "Probe: ONE 1 ms correlation (whole-kHz branch)",
            1, # Number of inputs
            None # parent
        )
        self.vs_1ms.set_update_time(0.05)
        self.vs_1ms.set_y_axis(0, 40)
        self.vs_1ms.enable_autoscale(False)
        self.vs_1ms.enable_grid(True)
        self.vs_1ms.set_x_axis_units("chips")
        self.vs_1ms.set_y_axis_units("")
        self.vs_1ms.set_ref_level(0)


        labels = ["1 ms", '', '', '', '',
            '', '', '', '', '']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ["blue", "red", "green", "black", "cyan",
            "magenta", "yellow", "dark red", "dark green", "dark blue"]
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]

        for i in range(1):
            if len(labels[i]) == 0:
                self.vs_1ms.set_line_label(i, "Data {0}".format(i))
            else:
                self.vs_1ms.set_line_label(i, labels[i])
            self.vs_1ms.set_line_width(i, widths[i])
            self.vs_1ms.set_line_color(i, colors[i])
            self.vs_1ms.set_line_alpha(i, alphas[i])

        self._vs_1ms_win = sip.wrapinstance(self.vs_1ms.qwidget(), Qt.QWidget)
        self.tabs_grid_layout_1.addWidget(self._vs_1ms_win, 0, 0, 1, 1)
        for r in range(0, 1):
            self.tabs_grid_layout_1.setRowStretch(r, 1)
        for c in range(0, 1):
            self.tabs_grid_layout_1.setColumnStretch(c, 1)
        self.ts_soft = qtgui.time_sink_f(
            300, #size
            50, #samp_rate
            "cos(phase change between bits): +1 same bit, -1 bit flip (6 s = 1 subframe)", #name
            4, #number of inputs
            None # parent
        )
        self.ts_soft.set_update_time(0.20)
        self.ts_soft.set_y_axis(-1.2, 1.2)

        self.ts_soft.set_y_label("cos", "")

        self.ts_soft.enable_tags(False)
        self.ts_soft.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, 0, "")
        self.ts_soft.enable_autoscale(False)
        self.ts_soft.enable_grid(True)
        self.ts_soft.enable_axis_labels(True)
        self.ts_soft.enable_control_panel(False)
        self.ts_soft.enable_stem_plot(False)


        labels = ["Ch 0", "Ch 1", "Ch 2", "Ch 3", 'Signal 5',
            'Signal 6', 'Signal 7', 'Signal 8', 'Signal 9', 'Signal 10']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ['blue', 'red', 'green', 'black', 'cyan',
            'magenta', 'yellow', 'dark red', 'dark green', 'dark blue']
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]
        styles = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        markers = [-1, -1, -1, -1, -1,
            -1, -1, -1, -1, -1]


        for i in range(4):
            if len(labels[i]) == 0:
                self.ts_soft.set_line_label(i, "Data {0}".format(i))
            else:
                self.ts_soft.set_line_label(i, labels[i])
            self.ts_soft.set_line_width(i, widths[i])
            self.ts_soft.set_line_color(i, colors[i])
            self.ts_soft.set_line_style(i, styles[i])
            self.ts_soft.set_line_marker(i, markers[i])
            self.ts_soft.set_line_alpha(i, alphas[i])

        self._ts_soft_win = sip.wrapinstance(self.ts_soft.qwidget(), Qt.QWidget)
        self.tabs_grid_layout_3.addWidget(self._ts_soft_win, 1, 1, 2, 1)
        for r in range(1, 3):
            self.tabs_grid_layout_3.setRowStretch(r, 1)
        for c in range(1, 2):
            self.tabs_grid_layout_3.setColumnStretch(c, 1)
        self.ts_bits = qtgui.time_sink_f(
            600, #size
            50, #samp_rate
            "Ch 0 decoded bits, last 12 s (tags = preamble candidates)", #name
            1, #number of inputs
            None # parent
        )
        self.ts_bits.set_update_time(0.20)
        self.ts_bits.set_y_axis(-0.5, 1.5)

        self.ts_bits.set_y_label("bit", "")

        self.ts_bits.enable_tags(True)
        self.ts_bits.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, 0, "")
        self.ts_bits.enable_autoscale(False)
        self.ts_bits.enable_grid(True)
        self.ts_bits.enable_axis_labels(True)
        self.ts_bits.enable_control_panel(False)
        self.ts_bits.enable_stem_plot(False)

        self.ts_bits.disable_legend()

        labels = ['Signal 1', 'Signal 2', 'Signal 3', 'Signal 4', 'Signal 5',
            'Signal 6', 'Signal 7', 'Signal 8', 'Signal 9', 'Signal 10']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ['blue', 'red', 'green', 'black', 'cyan',
            'magenta', 'yellow', 'dark red', 'dark green', 'dark blue']
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]
        styles = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        markers = [-1, -1, -1, -1, -1,
            -1, -1, -1, -1, -1]


        for i in range(1):
            if len(labels[i]) == 0:
                self.ts_bits.set_line_label(i, "Data {0}".format(i))
            else:
                self.ts_bits.set_line_label(i, labels[i])
            self.ts_bits.set_line_width(i, widths[i])
            self.ts_bits.set_line_color(i, colors[i])
            self.ts_bits.set_line_style(i, styles[i])
            self.ts_bits.set_line_marker(i, markers[i])
            self.ts_bits.set_line_alpha(i, alphas[i])

        self._ts_bits_win = sip.wrapinstance(self.ts_bits.qwidget(), Qt.QWidget)
        self.tabs_grid_layout_3.addWidget(self._ts_bits_win, 3, 0, 2, 2)
        for r in range(3, 5):
            self.tabs_grid_layout_3.setRowStretch(r, 1)
        for c in range(0, 2):
            self.tabs_grid_layout_3.setColumnStretch(c, 1)
        self.trk3 = gps_track_channel(
            ch=3,
            dll_gain=0.3,
            fll_gain=0.05,
            fll_narrow=0.05,
            samp_rate=samp_rate,
        )
        self.trk2 = gps_track_channel(
            ch=2,
            dll_gain=0.3,
            fll_gain=0.05,
            fll_narrow=0.05,
            samp_rate=samp_rate,
        )
        self.trk1 = gps_track_channel(
            ch=1,
            dll_gain=0.3,
            fll_gain=0.05,
            fll_narrow=0.05,
            samp_rate=samp_rate,
        )
        self.trk0 = gps_track_channel(
            ch=0,
            dll_gain=0.3,
            fll_gain=0.05,
            fll_narrow=0.05,
            samp_rate=samp_rate,
        )
        self.src_ci16 = blocks.file_source(gr.sizeof_short*1, base_path + '.sigmf-data', True, 0, 0)
        self.src_ci16.set_begin_tag(pmt.PMT_NIL)
        self.spec = qtgui.freq_sink_c(
            512, #size
            window.WIN_BLACKMAN_hARRIS, #wintype
            0, #fc
            disp_rate, #bw
            "Despread spectrum (offset from 1575.42 MHz, 250 Hz bins)", #name
            5,
            None # parent
        )
        self.spec.set_update_time(0.10)
        self.spec.set_y_axis((-55), (-15))
        self.spec.set_y_label('Relative Gain', 'dB')
        self.spec.set_trigger_mode(qtgui.TRIG_MODE_FREE, 0.0, 0, "")
        self.spec.enable_autoscale(False)
        self.spec.enable_grid(True)
        self.spec.set_fft_average(0.2)
        self.spec.enable_axis_labels(True)
        self.spec.enable_control_panel(True)
        self.spec.set_fft_window_normalized(False)



        labels = ["Raw input", "Ch 0", "Ch 1", "Ch 2", "Ch 3",
            '', '', '', '', '']
        widths = [1, 2, 2, 2, 2,
            1, 1, 1, 1, 1]
        colors = ["blue", "red", "green", "black", "cyan",
            "magenta", "yellow", "dark red", "dark green", "dark blue"]
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]

        for i in range(5):
            if len(labels[i]) == 0:
                self.spec.set_line_label(i, "Data {0}".format(i))
            else:
                self.spec.set_line_label(i, labels[i])
            self.spec.set_line_width(i, widths[i])
            self.spec.set_line_color(i, colors[i])
            self.spec.set_line_alpha(i, alphas[i])

        self._spec_win = sip.wrapinstance(self.spec.qwidget(), Qt.QWidget)
        self.tabs_grid_layout_0.addWidget(self._spec_win, 0, 0, 1, 2)
        for r in range(0, 1):
            self.tabs_grid_layout_0.setRowStretch(r, 1)
        for c in range(0, 2):
            self.tabs_grid_layout_0.setColumnStretch(c, 1)
        self.sched = sched.blk(samp_rate=samp_rate, m_max=m_max, n_noncoh=n_noncoh, warmup_ms=500, park_prn=park_prn, park_khz=park_khz)
        self.scale_ci16 = blocks.multiply_const_cc(1.0/32768)
        self._rf_gain_range = qtgui.Range(0, 49.6, 0.1, 40.2, 200)
        self._rf_gain_win = qtgui.RangeWidget(self._rf_gain_range, self.set_rf_gain, "RF gain [dB]", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_grid_layout.addWidget(self._rf_gain_win, 0, 0, 1, 1)
        for r in range(0, 1):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 1):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.rational_resampler_xxx_0 = filter.rational_resampler_ccc(
                interpolation=int(samp_rate),
                decimation=int(file_samp_rate),
                taps=[],
                fractional_bw=0)
        self._ppm_range = qtgui.Range(-100, 100, 1, 0, 200)
        self._ppm_win = qtgui.RangeWidget(self._ppm_range, self.set_ppm, "Freq corr [ppm]", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_grid_layout.addWidget(self._ppm_win, 0, 1, 1, 1)
        for r in range(0, 1):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(1, 2):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.p_iq = qtgui.time_sink_c(
            1000, #size
            1000, #samp_rate
            "Ch 0 prompt P, I and Q over 1 s: 50 bit/s navigation data (20 ms per bit)", #name
            1, #number of inputs
            None # parent
        )
        self.p_iq.set_update_time(0.10)
        self.p_iq.set_y_axis(-400, 400)

        self.p_iq.set_y_label("P", "")

        self.p_iq.enable_tags(False)
        self.p_iq.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, 0, "")
        self.p_iq.enable_autoscale(False)
        self.p_iq.enable_grid(True)
        self.p_iq.enable_axis_labels(True)
        self.p_iq.enable_control_panel(False)
        self.p_iq.enable_stem_plot(False)


        labels = ["I (in-phase)", "Q (quadrature)", 'Signal 3', 'Signal 4', 'Signal 5',
            'Signal 6', 'Signal 7', 'Signal 8', 'Signal 9', 'Signal 10']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ['blue', 'red', 'green', 'black', 'cyan',
            'magenta', 'yellow', 'dark red', 'dark green', 'dark blue']
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]
        styles = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        markers = [-1, -1, -1, -1, -1,
            -1, -1, -1, -1, -1]


        for i in range(2):
            if len(labels[i]) == 0:
                if (i % 2 == 0):
                    self.p_iq.set_line_label(i, "Re{{Data {0}}}".format(i/2))
                else:
                    self.p_iq.set_line_label(i, "Im{{Data {0}}}".format(i/2))
            else:
                self.p_iq.set_line_label(i, labels[i])
            self.p_iq.set_line_width(i, widths[i])
            self.p_iq.set_line_color(i, colors[i])
            self.p_iq.set_line_style(i, styles[i])
            self.p_iq.set_line_marker(i, markers[i])
            self.p_iq.set_line_alpha(i, alphas[i])

        self._p_iq_win = sip.wrapinstance(self.p_iq.qwidget(), Qt.QWidget)
        self.tabs_grid_layout_2.addWidget(self._p_iq_win, 0, 1, 1, 1)
        for r in range(0, 1):
            self.tabs_grid_layout_2.setRowStretch(r, 1)
        for c in range(1, 2):
            self.tabs_grid_layout_2.setColumnStretch(c, 1)
        self.null_el = blocks.null_sink(gr.sizeof_gr_complex*1)
        self.null_acq1 = blocks.null_sink(gr.sizeof_float*N)
        self.nb3 = gps_nav_bits(
            alpha=0.05,
        )
        self.nb2 = gps_nav_bits(
            alpha=0.05,
        )
        self.nb1 = gps_nav_bits(
            alpha=0.05,
        )
        self.nb0 = gps_nav_bits(
            alpha=0.05,
        )
        self.navdec = navdec.blk(n_ch=4)
        self.mp = blocks.complex_to_mag(1)
        self.ml = blocks.complex_to_mag(1)
        self.me = blocks.complex_to_mag(1)
        self.lastnav = qtgui.edit_box_msg(qtgui.STRING, "waiting for frame sync...", "Last decoded", False, True, "", None)
        self._lastnav_win = sip.wrapinstance(self.lastnav.qwidget(), Qt.QWidget)
        self.tabs_grid_layout_3.addWidget(self._lastnav_win, 0, 0, 1, 2)
        for r in range(0, 1):
            self.tabs_grid_layout_3.setRowStretch(r, 1)
        for c in range(0, 2):
            self.tabs_grid_layout_3.setColumnStretch(c, 1)
        self.ishort_to_complex = blocks.interleaved_short_to_complex(False, False,1.0)
        self.freq = qtgui.time_sink_f(
            5000, #size
            1000, #samp_rate
            "FLL frequency estimate (Hz), all channels, last 5 s", #name
            4, #number of inputs
            None # parent
        )
        self.freq.set_update_time(0.10)
        self.freq.set_y_axis(-10000, 10000)

        self.freq.set_y_label("Hz", "")

        self.freq.enable_tags(False)
        self.freq.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, 0, "")
        self.freq.enable_autoscale(True)
        self.freq.enable_grid(True)
        self.freq.enable_axis_labels(True)
        self.freq.enable_control_panel(False)
        self.freq.enable_stem_plot(False)


        labels = ["Ch 0", "Ch 1", "Ch 2", "Ch 3", 'Signal 5',
            'Signal 6', 'Signal 7', 'Signal 8', 'Signal 9', 'Signal 10']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ['blue', 'red', 'green', 'black', 'cyan',
            'magenta', 'yellow', 'dark red', 'dark green', 'dark blue']
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]
        styles = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        markers = [-1, -1, -1, -1, -1,
            -1, -1, -1, -1, -1]


        for i in range(4):
            if len(labels[i]) == 0:
                self.freq.set_line_label(i, "Data {0}".format(i))
            else:
                self.freq.set_line_label(i, labels[i])
            self.freq.set_line_width(i, widths[i])
            self.freq.set_line_color(i, colors[i])
            self.freq.set_line_style(i, styles[i])
            self.freq.set_line_marker(i, markers[i])
            self.freq.set_line_alpha(i, alphas[i])

        self._freq_win = sip.wrapinstance(self.freq.qwidget(), Qt.QWidget)
        self.tabs_grid_layout_2.addWidget(self._freq_win, 2, 0, 1, 1)
        for r in range(2, 3):
            self.tabs_grid_layout_2.setRowStretch(r, 1)
        for c in range(0, 1):
            self.tabs_grid_layout_2.setColumnStretch(c, 1)
        self.epl = qtgui.time_sink_f(
            1000, #size
            1000, #samp_rate
            "Ch 0 |E|, |P|, |L|: on lock |P| on top, |E| = |L| about half of it", #name
            3, #number of inputs
            None # parent
        )
        self.epl.set_update_time(0.10)
        self.epl.set_y_axis(0, 400)

        self.epl.set_y_label("|corr|", "")

        self.epl.enable_tags(False)
        self.epl.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, 0, "")
        self.epl.enable_autoscale(False)
        self.epl.enable_grid(True)
        self.epl.enable_axis_labels(True)
        self.epl.enable_control_panel(False)
        self.epl.enable_stem_plot(False)


        labels = ["|E| early", "|P| prompt", "|L| late", 'Signal 4', 'Signal 5',
            'Signal 6', 'Signal 7', 'Signal 8', 'Signal 9', 'Signal 10']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ['blue', 'red', 'green', 'black', 'cyan',
            'magenta', 'yellow', 'dark red', 'dark green', 'dark blue']
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]
        styles = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        markers = [-1, -1, -1, -1, -1,
            -1, -1, -1, -1, -1]


        for i in range(3):
            if len(labels[i]) == 0:
                self.epl.set_line_label(i, "Data {0}".format(i))
            else:
                self.epl.set_line_label(i, labels[i])
            self.epl.set_line_width(i, widths[i])
            self.epl.set_line_color(i, colors[i])
            self.epl.set_line_style(i, styles[i])
            self.epl.set_line_marker(i, markers[i])
            self.epl.set_line_alpha(i, alphas[i])

        self._epl_win = sip.wrapinstance(self.epl.qwidget(), Qt.QWidget)
        self.tabs_grid_layout_2.addWidget(self._epl_win, 1, 0, 1, 1)
        for r in range(1, 2):
            self.tabs_grid_layout_2.setRowStretch(r, 1)
        for c in range(0, 1):
            self.tabs_grid_layout_2.setColumnStretch(c, 1)
        self.dll = qtgui.time_sink_f(
            1000, #size
            1000, #samp_rate
            "DLL discriminator (chips): replica minus signal, all channels", #name
            4, #number of inputs
            None # parent
        )
        self.dll.set_update_time(0.10)
        self.dll.set_y_axis(-0.5, 0.5)

        self.dll.set_y_label("chips", "")

        self.dll.enable_tags(False)
        self.dll.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, 0, "")
        self.dll.enable_autoscale(False)
        self.dll.enable_grid(True)
        self.dll.enable_axis_labels(True)
        self.dll.enable_control_panel(False)
        self.dll.enable_stem_plot(False)


        labels = ["Ch 0", "Ch 1", "Ch 2", "Ch 3", 'Signal 5',
            'Signal 6', 'Signal 7', 'Signal 8', 'Signal 9', 'Signal 10']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ['blue', 'red', 'green', 'black', 'cyan',
            'magenta', 'yellow', 'dark red', 'dark green', 'dark blue']
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]
        styles = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        markers = [-1, -1, -1, -1, -1,
            -1, -1, -1, -1, -1]


        for i in range(4):
            if len(labels[i]) == 0:
                self.dll.set_line_label(i, "Data {0}".format(i))
            else:
                self.dll.set_line_label(i, labels[i])
            self.dll.set_line_width(i, widths[i])
            self.dll.set_line_color(i, colors[i])
            self.dll.set_line_style(i, styles[i])
            self.dll.set_line_marker(i, markers[i])
            self.dll.set_line_alpha(i, alphas[i])

        self._dll_win = sip.wrapinstance(self.dll.qwidget(), Qt.QWidget)
        self.tabs_grid_layout_2.addWidget(self._dll_win, 1, 1, 1, 1)
        for r in range(1, 2):
            self.tabs_grid_layout_2.setRowStretch(r, 1)
        for c in range(1, 2):
            self.tabs_grid_layout_2.setColumnStretch(c, 1)
        self.decider = decider.blk(samp_rate=samp_rate, m_max=m_max, n_noncoh=n_noncoh, threshold=threshold, n_ch=4, min_dof=5.0)
        self.dec_raw = filter.fir_filter_ccf(decim, lpf_taps)
        self.dec_raw.declare_sample_delay(0)
        self.dec_c3 = filter.fir_filter_ccf(decim, lpf_taps)
        self.dec_c3.declare_sample_delay(0)
        self.dec_c2 = filter.fir_filter_ccf(decim, lpf_taps)
        self.dec_c2.declare_sample_delay(0)
        self.dec_c1 = filter.fir_filter_ccf(decim, lpf_taps)
        self.dec_c1.declare_sample_delay(0)
        self.dec_c0 = filter.fir_filter_ccf(decim, lpf_taps)
        self.dec_c0.declare_sample_delay(0)
        self.dcblk = filter.dc_blocker_cc(1024, True)
        self._datatype_tool_bar = Qt.QToolBar(self)

        if None:
            self._datatype_formatter = None
        else:
            self._datatype_formatter = lambda x: str(x)

        self._datatype_tool_bar.addWidget(Qt.QLabel("core:datatype"))
        self._datatype_label = Qt.QLabel(str(self._datatype_formatter(self.datatype)))
        self._datatype_tool_bar.addWidget(self._datatype_label)
        self.top_layout.addWidget(self._datatype_tool_bar)
        self.const_p = qtgui.const_sink_c(
            500, #size
            "Prompt correlator P (each dot = 1 ms)", #name
            4, #number of inputs
            None # parent
        )
        self.const_p.set_update_time(0.10)
        self.const_p.set_y_axis((-400), 400)
        self.const_p.set_x_axis((-400), 400)
        self.const_p.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, "")
        self.const_p.enable_autoscale(False)
        self.const_p.enable_grid(True)
        self.const_p.enable_axis_labels(True)


        labels = ["Ch 0", "Ch 1", "Ch 2", "Ch 3", '',
            '', '', '', '', '']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ["blue", "red", "green", "black", "cyan",
            "magenta", "yellow", "dark red", "dark green", "dark blue"]
        styles = [0, 0, 0, 0, 0,
            0, 0, 0, 0, 0]
        markers = [0, 0, 0, 0, 0,
            0, 0, 0, 0, 0]
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]

        for i in range(4):
            if len(labels[i]) == 0:
                self.const_p.set_line_label(i, "Data {0}".format(i))
            else:
                self.const_p.set_line_label(i, labels[i])
            self.const_p.set_line_width(i, widths[i])
            self.const_p.set_line_color(i, colors[i])
            self.const_p.set_line_style(i, styles[i])
            self.const_p.set_line_marker(i, markers[i])
            self.const_p.set_line_alpha(i, alphas[i])

        self._const_p_win = sip.wrapinstance(self.const_p.qwidget(), Qt.QWidget)
        self.tabs_grid_layout_2.addWidget(self._const_p_win, 0, 0, 1, 1)
        for r in range(0, 1):
            self.tabs_grid_layout_2.setRowStretch(r, 1)
        for c in range(0, 1):
            self.tabs_grid_layout_2.setColumnStretch(c, 1)
        self.cn0 = qtgui.number_sink(
            gr.sizeof_float,
            0,
            qtgui.NUM_GRAPH_HORIZ,
            4,
            None # parent
        )
        self.cn0.set_update_time(0.2)
        self.cn0.set_title("C/N0 per channel [dB-Hz] (0 = idle)")

        labels = ["Ch 0", "Ch 1", "Ch 2", "Ch 3", '',
            '', '', '', '', '']
        units = ["dB-Hz", "dB-Hz", "dB-Hz", "dB-Hz", '',
            '', '', '', '', '']
        colors = [("black", "black"), ("black", "black"), ("black", "black"), ("black", "black"), ("black", "black"),
            ("black", "black"), ("black", "black"), ("black", "black"), ("black", "black"), ("black", "black")]
        factor = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]

        for i in range(4):
            self.cn0.set_min(i, 20)
            self.cn0.set_max(i, 55)
            self.cn0.set_color(i, colors[i][0], colors[i][1])
            if len(labels[i]) == 0:
                self.cn0.set_label(i, "Data {0}".format(i))
            else:
                self.cn0.set_label(i, labels[i])
            self.cn0.set_unit(i, units[i])
            self.cn0.set_factor(i, factor[i])

        self.cn0.enable_autoscale(False)
        self._cn0_win = sip.wrapinstance(self.cn0.qwidget(), Qt.QWidget)
        self.tabs_grid_layout_2.addWidget(self._cn0_win, 2, 1, 1, 1)
        for r in range(2, 3):
            self.tabs_grid_layout_2.setRowStretch(r, 1)
        for c in range(1, 2):
            self.tabs_grid_layout_2.setColumnStretch(c, 1)
        self.blocks_throttle2_0 = blocks.throttle( gr.sizeof_gr_complex*1, samp_rate, True, 0 if "auto" == "auto" else max( int(float(0.1) * samp_rate) if "auto" == "time" else int(0.1), 1) )
        self.b2f = blocks.char_to_float(1, 1)
        self.agc = analog.agc_cc((2e-5), 1.0, 1.0, 65536)
        self.acq_dopp = qtgui.time_sink_f(
            42, #size
            2, #samp_rate
            "Decision: Doppler column at best code phase (x = kHz above -10 kHz)", #name
            0, #number of inputs
            None # parent
        )
        self.acq_dopp.set_update_time(0.10)
        self.acq_dopp.set_y_axis(0, 10)

        self.acq_dopp.set_y_label('peak/mean', "")

        self.acq_dopp.enable_tags(False)
        self.acq_dopp.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, 0, "")
        self.acq_dopp.enable_autoscale(True)
        self.acq_dopp.enable_grid(True)
        self.acq_dopp.enable_axis_labels(True)
        self.acq_dopp.enable_control_panel(False)
        self.acq_dopp.enable_stem_plot(False)

        self.acq_dopp.disable_legend()

        labels = ['Signal 1', 'Signal 2', 'Signal 3', 'Signal 4', 'Signal 5',
            'Signal 6', 'Signal 7', 'Signal 8', 'Signal 9', 'Signal 10']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ['blue', 'red', 'green', 'black', 'cyan',
            'magenta', 'yellow', 'dark red', 'dark green', 'dark blue']
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]
        styles = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        markers = [-1, -1, -1, -1, -1,
            -1, -1, -1, -1, -1]


        for i in range(1):
            if len(labels[i]) == 0:
                self.acq_dopp.set_line_label(i, "Data {0}".format(i))
            else:
                self.acq_dopp.set_line_label(i, labels[i])
            self.acq_dopp.set_line_width(i, widths[i])
            self.acq_dopp.set_line_color(i, colors[i])
            self.acq_dopp.set_line_style(i, styles[i])
            self.acq_dopp.set_line_marker(i, markers[i])
            self.acq_dopp.set_line_alpha(i, alphas[i])

        self._acq_dopp_win = sip.wrapinstance(self.acq_dopp.qwidget(), Qt.QWidget)
        self.tabs_grid_layout_1.addWidget(self._acq_dopp_win, 1, 1, 1, 1)
        for r in range(1, 2):
            self.tabs_grid_layout_1.setRowStretch(r, 1)
        for c in range(1, 2):
            self.tabs_grid_layout_1.setColumnStretch(c, 1)
        self.acq_corr = qtgui.time_sink_f(
            2048, #size
            samp_rate/1.023e6, #samp_rate
            "Decision: best Doppler row vs code phase (x = chips), last PRN", #name
            0, #number of inputs
            None # parent
        )
        self.acq_corr.set_update_time(0.10)
        self.acq_corr.set_y_axis(0, 10)

        self.acq_corr.set_y_label('peak/mean', "")

        self.acq_corr.enable_tags(False)
        self.acq_corr.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, 0, "")
        self.acq_corr.enable_autoscale(True)
        self.acq_corr.enable_grid(True)
        self.acq_corr.enable_axis_labels(True)
        self.acq_corr.enable_control_panel(False)
        self.acq_corr.enable_stem_plot(False)

        self.acq_corr.disable_legend()

        labels = ['Signal 1', 'Signal 2', 'Signal 3', 'Signal 4', 'Signal 5',
            'Signal 6', 'Signal 7', 'Signal 8', 'Signal 9', 'Signal 10']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ['blue', 'red', 'green', 'black', 'cyan',
            'magenta', 'yellow', 'dark red', 'dark green', 'dark blue']
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]
        styles = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        markers = [-1, -1, -1, -1, -1,
            -1, -1, -1, -1, -1]


        for i in range(1):
            if len(labels[i]) == 0:
                self.acq_corr.set_line_label(i, "Data {0}".format(i))
            else:
                self.acq_corr.set_line_label(i, labels[i])
            self.acq_corr.set_line_width(i, widths[i])
            self.acq_corr.set_line_color(i, colors[i])
            self.acq_corr.set_line_style(i, styles[i])
            self.acq_corr.set_line_marker(i, markers[i])
            self.acq_corr.set_line_alpha(i, alphas[i])

        self._acq_corr_win = sip.wrapinstance(self.acq_corr.qwidget(), Qt.QWidget)
        self.tabs_grid_layout_1.addWidget(self._acq_corr_win, 1, 0, 1, 1)
        for r in range(1, 2):
            self.tabs_grid_layout_1.setRowStretch(r, 1)
        for c in range(0, 1):
            self.tabs_grid_layout_1.setColumnStretch(c, 1)
        self.acq_bars = qtgui.time_sink_f(
            32, #size
            1, #samp_rate
            "Decision: peak/mean per PRN (x = PRN - 1), threshold 3.5", #name
            0, #number of inputs
            None # parent
        )
        self.acq_bars.set_update_time(0.10)
        self.acq_bars.set_y_axis(0, 25)

        self.acq_bars.set_y_label('peak/mean', "")

        self.acq_bars.enable_tags(False)
        self.acq_bars.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, 0, "")
        self.acq_bars.enable_autoscale(False)
        self.acq_bars.enable_grid(True)
        self.acq_bars.enable_axis_labels(True)
        self.acq_bars.enable_control_panel(False)
        self.acq_bars.enable_stem_plot(True)

        self.acq_bars.disable_legend()

        labels = ['Signal 1', 'Signal 2', 'Signal 3', 'Signal 4', 'Signal 5',
            'Signal 6', 'Signal 7', 'Signal 8', 'Signal 9', 'Signal 10']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ['blue', 'red', 'green', 'black', 'cyan',
            'magenta', 'yellow', 'dark red', 'dark green', 'dark blue']
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]
        styles = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        markers = [-1, -1, -1, -1, -1,
            -1, -1, -1, -1, -1]


        for i in range(1):
            if len(labels[i]) == 0:
                self.acq_bars.set_line_label(i, "Data {0}".format(i))
            else:
                self.acq_bars.set_line_label(i, labels[i])
            self.acq_bars.set_line_width(i, widths[i])
            self.acq_bars.set_line_color(i, colors[i])
            self.acq_bars.set_line_style(i, styles[i])
            self.acq_bars.set_line_marker(i, markers[i])
            self.acq_bars.set_line_alpha(i, alphas[i])

        self._acq_bars_win = sip.wrapinstance(self.acq_bars.qwidget(), Qt.QWidget)
        self.tabs_grid_layout_1.addWidget(self._acq_bars_win, 2, 0, 1, 2)
        for r in range(2, 3):
            self.tabs_grid_layout_1.setRowStretch(r, 1)
        for c in range(0, 2):
            self.tabs_grid_layout_1.setColumnStretch(c, 1)
        self.acq1 = gps_acq_branch(
            N=N,
            f_off=(-500),
            n_noncoh=n_noncoh,
            samp_rate=samp_rate,
        )
        self.acq0 = gps_acq_branch(
            N=N,
            f_off=0,
            n_noncoh=n_noncoh,
            samp_rate=samp_rate,
        )


        ##################################################
        # Connections
        ##################################################
        self.msg_connect((self.decider, 'acq'), (self.acq_bars, 'in'))
        self.msg_connect((self.decider, 'corr'), (self.acq_corr, 'in'))
        self.msg_connect((self.decider, 'dopp'), (self.acq_dopp, 'in'))
        self.msg_connect((self.decider, 'assign'), (self.sched, 'status'))
        self.msg_connect((self.decider, 'assign'), (self.trk0, 'assign'))
        self.msg_connect((self.decider, 'assign'), (self.trk1, 'assign'))
        self.msg_connect((self.decider, 'assign'), (self.trk2, 'assign'))
        self.msg_connect((self.decider, 'assign'), (self.trk3, 'assign'))
        self.msg_connect((self.navdec, 'text'), (self.lastnav, 'val'))
        self.msg_connect((self.trk0, 'status'), (self.decider, 'status'))
        self.msg_connect((self.trk0, 'status'), (self.navdec, 'status'))
        self.msg_connect((self.trk0, 'status'), (self.sched, 'status'))
        self.msg_connect((self.trk1, 'status'), (self.decider, 'status'))
        self.msg_connect((self.trk1, 'status'), (self.navdec, 'status'))
        self.msg_connect((self.trk1, 'status'), (self.sched, 'status'))
        self.msg_connect((self.trk2, 'status'), (self.decider, 'status'))
        self.msg_connect((self.trk2, 'status'), (self.navdec, 'status'))
        self.msg_connect((self.trk2, 'status'), (self.sched, 'status'))
        self.msg_connect((self.trk3, 'status'), (self.decider, 'status'))
        self.msg_connect((self.trk3, 'status'), (self.navdec, 'status'))
        self.msg_connect((self.trk3, 'status'), (self.sched, 'status'))
        self.connect((self.acq0, 1), (self.decider, 0))
        self.connect((self.acq0, 0), (self.vs_1ms, 0))
        self.connect((self.acq0, 1), (self.vs_20ms, 0))
        self.connect((self.acq1, 1), (self.decider, 1))
        self.connect((self.acq1, 0), (self.null_acq1, 0))
        self.connect((self.acq1, 1), (self.vs_20ms, 1))
        self.connect((self.agc, 0), (self.acq0, 0))
        self.connect((self.agc, 0), (self.acq1, 0))
        self.connect((self.agc, 0), (self.dec_raw, 0))
        self.connect((self.agc, 0), (self.sched, 0))
        self.connect((self.agc, 0), (self.trk0, 0))
        self.connect((self.agc, 0), (self.trk1, 0))
        self.connect((self.agc, 0), (self.trk2, 0))
        self.connect((self.agc, 0), (self.trk3, 0))
        self.connect((self.b2f, 0), (self.ts_bits, 0))
        self.connect((self.blocks_throttle2_0, 0), (self.dcblk, 0))
        self.connect((self.dcblk, 0), (self.agc, 0))
        self.connect((self.dec_c0, 0), (self.spec, 1))
        self.connect((self.dec_c0, 0), (self.wf_c0, 0))
        self.connect((self.dec_c1, 0), (self.spec, 2))
        self.connect((self.dec_c2, 0), (self.spec, 3))
        self.connect((self.dec_c3, 0), (self.spec, 4))
        self.connect((self.dec_raw, 0), (self.spec, 0))
        self.connect((self.dec_raw, 0), (self.wf_raw, 0))
        self.connect((self.ishort_to_complex, 0), (self.scale_ci16, 0))
        self.connect((self.me, 0), (self.epl, 0))
        self.connect((self.ml, 0), (self.epl, 2))
        self.connect((self.mp, 0), (self.epl, 1))
        self.connect((self.nb0, 0), (self.b2f, 0))
        self.connect((self.nb0, 0), (self.navdec, 0))
        self.connect((self.nb0, 1), (self.ts_soft, 0))
        self.connect((self.nb0, 2), (self.vs_bitsync, 0))
        self.connect((self.nb1, 0), (self.navdec, 1))
        self.connect((self.nb1, 1), (self.ts_soft, 1))
        self.connect((self.nb1, 2), (self.vs_bitsync, 1))
        self.connect((self.nb2, 0), (self.navdec, 2))
        self.connect((self.nb2, 1), (self.ts_soft, 2))
        self.connect((self.nb2, 2), (self.vs_bitsync, 2))
        self.connect((self.nb3, 0), (self.navdec, 3))
        self.connect((self.nb3, 1), (self.ts_soft, 3))
        self.connect((self.nb3, 2), (self.vs_bitsync, 3))
        self.connect((self.rational_resampler_xxx_0, 0), (self.blocks_throttle2_0, 0))
        self.connect((self.scale_ci16, 0), (self.rational_resampler_xxx_0, 0))
        self.connect((self.sched, 0), (self.acq0, 1))
        self.connect((self.sched, 0), (self.acq1, 1))
        self.connect((self.src_ci16, 0), (self.ishort_to_complex, 0))
        self.connect((self.trk0, 6), (self.cn0, 0))
        self.connect((self.trk0, 1), (self.const_p, 0))
        self.connect((self.trk0, 0), (self.dec_c0, 0))
        self.connect((self.trk0, 4), (self.dll, 0))
        self.connect((self.trk0, 5), (self.freq, 0))
        self.connect((self.trk0, 2), (self.me, 0))
        self.connect((self.trk0, 3), (self.ml, 0))
        self.connect((self.trk0, 1), (self.mp, 0))
        self.connect((self.trk0, 1), (self.nb0, 0))
        self.connect((self.trk0, 1), (self.p_iq, 0))
        self.connect((self.trk1, 6), (self.cn0, 1))
        self.connect((self.trk1, 1), (self.const_p, 1))
        self.connect((self.trk1, 0), (self.dec_c1, 0))
        self.connect((self.trk1, 4), (self.dll, 1))
        self.connect((self.trk1, 5), (self.freq, 1))
        self.connect((self.trk1, 1), (self.nb1, 0))
        self.connect((self.trk1, 3), (self.null_el, 1))
        self.connect((self.trk1, 2), (self.null_el, 0))
        self.connect((self.trk2, 6), (self.cn0, 2))
        self.connect((self.trk2, 1), (self.const_p, 2))
        self.connect((self.trk2, 0), (self.dec_c2, 0))
        self.connect((self.trk2, 4), (self.dll, 2))
        self.connect((self.trk2, 5), (self.freq, 2))
        self.connect((self.trk2, 1), (self.nb2, 0))
        self.connect((self.trk2, 3), (self.null_el, 3))
        self.connect((self.trk2, 2), (self.null_el, 2))
        self.connect((self.trk3, 6), (self.cn0, 3))
        self.connect((self.trk3, 1), (self.const_p, 3))
        self.connect((self.trk3, 0), (self.dec_c3, 0))
        self.connect((self.trk3, 4), (self.dll, 3))
        self.connect((self.trk3, 5), (self.freq, 3))
        self.connect((self.trk3, 1), (self.nb3, 0))
        self.connect((self.trk3, 2), (self.null_el, 4))
        self.connect((self.trk3, 3), (self.null_el, 5))


    def closeEvent(self, event):
        self.settings = Qt.QSettings("GNU Radio", "gps_l1_lab")
        self.settings.setValue("geometry", self.saveGeometry())
        self.stop()
        self.wait()

        event.accept()

    def get_base_path(self):
        return self.base_path

    def set_base_path(self, base_path):
        self.base_path = base_path
        self.set_meta(json.load(open(self.base_path + '.sigmf-meta')))
        self.src_ci16.open(self.base_path + '.sigmf-data', True)

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.set_N(int(round(self.samp_rate*1e-3)))
        self.set_chips_per_sample(1.023e6/self.samp_rate)
        self.set_disp_rate(self.samp_rate/self.decim)
        self.set_lpf_taps(firdes.low_pass(1.0, self.samp_rate, 22e3, 16e3))
        self.acq0.set_samp_rate(self.samp_rate)
        self.acq1.set_samp_rate(self.samp_rate)
        self.acq_corr.set_samp_rate(self.samp_rate/1.023e6)
        self.blocks_throttle2_0.set_sample_rate(self.samp_rate)
        self.trk0.set_samp_rate(self.samp_rate)
        self.trk1.set_samp_rate(self.samp_rate)
        self.trk2.set_samp_rate(self.samp_rate)
        self.trk3.set_samp_rate(self.samp_rate)

    def get_meta(self):
        return self.meta

    def set_meta(self, meta):
        self.meta = meta
        self.set_center_freq_0(float(self.meta['captures'][0].get('core:frequency', 0)))
        self.set_datatype(self.meta['global']['core:datatype'])
        self.set_file_samp_rate(float(self.meta['global']['core:sample_rate']))

    def get_decim(self):
        return self.decim

    def set_decim(self, decim):
        self.decim = decim
        self.set_disp_rate(self.samp_rate/self.decim)

    def get_threshold(self):
        return self.threshold

    def set_threshold(self, threshold):
        self.threshold = threshold

    def get_rf_gain(self):
        return self.rf_gain

    def set_rf_gain(self, rf_gain):
        self.rf_gain = rf_gain

    def get_ppm(self):
        return self.ppm

    def set_ppm(self, ppm):
        self.ppm = ppm

    def get_park_prn(self):
        return self.park_prn

    def set_park_prn(self, park_prn):
        self.park_prn = park_prn
        self.sched.park_prn = self.park_prn

    def get_park_khz(self):
        return self.park_khz

    def set_park_khz(self, park_khz):
        self.park_khz = park_khz
        self.sched.park_khz = self.park_khz

    def get_n_noncoh(self):
        return self.n_noncoh

    def set_n_noncoh(self, n_noncoh):
        self.n_noncoh = n_noncoh
        self.acq0.set_n_noncoh(self.n_noncoh)
        self.acq1.set_n_noncoh(self.n_noncoh)

    def get_m_max(self):
        return self.m_max

    def set_m_max(self, m_max):
        self.m_max = m_max
        self.decider.m_max = self.m_max
        self.sched.m_max = self.m_max

    def get_lpf_taps(self):
        return self.lpf_taps

    def set_lpf_taps(self, lpf_taps):
        self.lpf_taps = lpf_taps
        self.dec_c0.set_taps(self.lpf_taps)
        self.dec_c1.set_taps(self.lpf_taps)
        self.dec_c2.set_taps(self.lpf_taps)
        self.dec_c3.set_taps(self.lpf_taps)
        self.dec_raw.set_taps(self.lpf_taps)

    def get_file_samp_rate(self):
        return self.file_samp_rate

    def set_file_samp_rate(self, file_samp_rate):
        self.file_samp_rate = file_samp_rate

    def get_disp_rate(self):
        return self.disp_rate

    def set_disp_rate(self, disp_rate):
        self.disp_rate = disp_rate
        self.spec.set_frequency_range(0, self.disp_rate)
        self.wf_c0.set_frequency_range(0, self.disp_rate)
        self.wf_raw.set_frequency_range(0, self.disp_rate)

    def get_datatype(self):
        return self.datatype

    def set_datatype(self, datatype):
        self.datatype = datatype
        Qt.QMetaObject.invokeMethod(self._datatype_label, "setText", Qt.Q_ARG("QString", str(self._datatype_formatter(self.datatype))))

    def get_chips_per_sample(self):
        return self.chips_per_sample

    def set_chips_per_sample(self, chips_per_sample):
        self.chips_per_sample = chips_per_sample
        self.vs_1ms.set_x_axis(0, self.chips_per_sample)
        self.vs_20ms.set_x_axis(0, self.chips_per_sample)

    def get_center_freq_0(self):
        return self.center_freq_0

    def set_center_freq_0(self, center_freq_0):
        self.center_freq_0 = center_freq_0

    def get_center_freq(self):
        return self.center_freq

    def set_center_freq(self, center_freq):
        self.center_freq = center_freq

    def get_N(self):
        return self.N

    def set_N(self, N):
        self.N = N
        self.acq0.set_N(self.N)
        self.acq1.set_N(self.N)




def main(top_block_cls=gps_l1_lab, options=None):

    qapp = Qt.QApplication(sys.argv)

    tb = top_block_cls()

    tb.start()

    tb.show()

    def sig_handler(sig=None, frame=None):
        tb.stop()
        tb.wait()

        Qt.QApplication.quit()

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    timer = Qt.QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)

    qapp.exec_()

if __name__ == '__main__':
    main()
