import time

from hub.dev import GEN_SHAPES, SimDevice


class FakeSerial(object):
    LEN = {0x01: 3, 0x02: 3, 0x03: 4, 0x04: 5, 0x05: 2, 0x06: 3, 0x07: 3, 0x08: 3,
           0x0A: 2, 0xEF: 1, 0xF0: 1, 0xC2: 1, 0xC3: 1, 0xC4: 1, 0xC6: 2,
           0xD0: 10, 0xD1: 2, 0xD2: 2}
    WIFI_UP_S = 0.6
    SD_MB = 7580

    def __init__(self):
        self.sim = SimDevice()
        self.sim.open()
        self.buf = bytearray()
        self.out = bytearray()
        self.ssid = ""
        self.fuser = ""
        self.wstate = 0
        self.wt0 = 0.0
        self.fon = False

    def reset_input_buffer(self):
        self.out = bytearray()

    def write(self, data):
        self.buf += data
        while self.buf:
            c = self.buf[0]
            if c == 0x09:
                if len(self.buf) < 5 or len(self.buf) < 5 + self.buf[4]:
                    return
                n = 5 + self.buf[4]
            elif c in (0xC1, 0xC5):
                if len(self.buf) < 3 or len(self.buf) < 3 + self.buf[1] + self.buf[2]:
                    return
                n = 3 + self.buf[1] + self.buf[2]
            else:
                n = self.LEN.get(c, 1)
                if len(self.buf) < n:
                    return
            frame = bytes(self.buf[:n])
            del self.buf[:n]
            self.out += self.reply(frame)
        return len(data)

    def reply(self, f):
        s = self.sim
        c = f[0]
        if c == 0x01:
            return b"AA" if s.do(f[1], f[2]) else b"XX"
        if c == 0x02:
            v = s.di(f[1])
            return b"XX" if v is None else (b"A1" if v else b"A0")
        if c == 0x05:
            v = s.ai_raw(f[1])
            return (b"%d\r\n" % v) if v is not None else b"-2\r\n"
        if c == 0x06:
            return b"AA" if s.ao_raw(f[1], f[2]) else b"XX"
        if c == 0x07:
            return b"AA" if s.pwm_raw(f[1], f[2]) else b"XX"
        if c == 0x08:
            time.sleep(0.001)
            return b"AA" if f[1] < 2 else b"XX"
        if c in (0x03, 0x04, 0x09, 0x0A, 0xF0):
            time.sleep(0.001)
            if (c == 0x04 and f[1] >= 16) or (c == 0x0A and f[1] >= 2):
                return b"XX"
            return b"AA"
        if c == 0xD0:
            shape = [k for k, v in GEN_SHAPES.items() if v == f[2]]
            if not shape:
                return b"XX"
            mhz = (f[3] << 24) | (f[4] << 16) | (f[5] << 8) | f[6]
            k = s.vref / 255.0
            return b"AA" if s.dacgen(f[1], shape[0], mhz / 1000.0, f[7] * k, f[8] * k,
                                     f[9] / 100.0) else b"XX"
        if c == 0xD1:
            return b"AA" if s.dacgen_stop(f[1]) else b"XX"
        if c == 0xD2:
            st = s.dacgen_status(f[1])
            if st is None:
                return b"-2\r\n"
            return ("%d,%d,%d,%d,%d\r\n" % (st["on"], st["shape"], round(st["f"] * 1000),
                                             st["fs"], round(st["fmax"] * 1000))).encode()
        if c == 0xEF:
            return b"LV,ESP32-ONLINE,3.0.0,00:00:00:00:00:00,SIM,10,3,6,1,2,2,2\r\n"
        if 0xC1 <= c <= 0xC6:
            return self.online(f)
        return b"XX"

    def online(self, f):
        c = f[0]
        if self.wstate == 1 and time.time() - self.wt0 > self.WIFI_UP_S:
            self.wstate = 2
        if c == 0xC1:
            ok = 1 <= f[1] <= 32 and f[2] <= 63
            if ok:
                self.ssid = f[3:3 + f[1]].decode("utf-8", "replace")
            return b"AA" if ok else b"XX"
        if c == 0xC2:
            if self.wstate == 0 and not self.ssid:
                return b"XX"
            if self.wstate == 0:
                self.wstate = 1
                self.wt0 = time.time()
            return b"AA"
        if c == 0xC3:
            up = self.wstate == 2
            return ("%d,%s,%d,%d,%d\r\n" % (self.wstate, "10.0.0.50" if up else "0.0.0.0",
                                             -55 if up else 0, 1 if self.fon else 0,
                                             self.SD_MB if self.fon else 0)).encode()
        if c == 0xC4:
            self.wstate = 0
            self.fon = False
            return b"AA"
        if c == 0xC5:
            ok = 1 <= f[1] <= 32 and 1 <= f[2] <= 32
            if ok:
                self.fuser = f[3:3 + f[1]].decode("utf-8", "replace")
            return b"AA" if ok else b"XX"
        if not f[1]:
            self.fon = False
            return b"AA"
        if self.wstate != 2 or not self.fuser:
            return b"XX"
        self.fon = True
        return b"AA"

    def read(self, n=1):
        if not self.out:
            time.sleep(0.0005)
            return b""
        r = bytes(self.out[:n])
        del self.out[:n]
        return r

    def close(self):
        pass
