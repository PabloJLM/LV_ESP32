import time

from hub.dev import GEN_SHAPES, SimDevice


class FakeSerial(object):
    LEN = {0x01: 3, 0x02: 3, 0x03: 4, 0x04: 5, 0x05: 2, 0x06: 3, 0x07: 3, 0x08: 3,
           0x0A: 2, 0xEF: 1, 0xF0: 1, 0xC2: 1, 0xC3: 1, 0xC4: 1, 0xC6: 2,
           0xD0: 10, 0xD1: 2, 0xD2: 2}

    def __init__(self):
        self.sim = SimDevice()
        self.sim.open()
        self.buf = bytearray()
        self.out = bytearray()

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
            return b"LV,ESP32,3.0.0,-,SIM,10,3,6,1,2,2,2\r\n"
        return b"XX"

    def read(self, n=1):
        if not self.out:
            time.sleep(0.0005)
            return b""
        r = bytes(self.out[:n])
        del self.out[:n]
        return r

    def close(self):
        pass
