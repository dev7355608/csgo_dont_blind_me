import struct
import platform
import xml.etree.ElementTree as ET
from io import BytesIO


__all__ = ['read_icc_ramp']

RGB = struct.unpack('>I', b'RGB ')[0]
VCGT = struct.unpack('>I', b'vcgt')[0]
MLUT = struct.unpack('>I', b'mLUT')[0]
MS00 = struct.unpack('>I', b'MS00')[0]
MS10 = struct.unpack('>I', b'MS10')[0]


def unpack(fmt, fp):
    size = struct.calcsize(fmt)
    buffer = fp.read(size)
    return struct.unpack('>' + fmt, buffer)


def read_icc_ramp(file_or_bytes, size=256, system=None):
    if isinstance(file_or_bytes, bytes):
        fp = BytesIO(file_or_bytes)
    else:
        fp = file_or_bytes

    assert size > 1

    if system is None:
        system = platform.system()

    ramp = None
    ramp_x = None

    fp.seek(16)

    color_space = unpack('I', fp)[0]
    assert color_space == RGB

    fp.seek(128)

    num_tags = unpack('I', fp)[0]

    cur_pos = fp.tell()

    for i in range(num_tags):
        fp.seek(cur_pos)

        tag_name, tag_offset, tag_size = unpack('III', fp)

        cur_pos = fp.tell()

        if tag_name == MS00 and system == 'Windows':
            fp.seek(tag_offset)

            tag_type, _, cdmp_offset, cdmp_size = unpack('4I', fp)

            if tag_type != MS10:
                continue

            fp.seek(tag_offset + cdmp_offset)
            cdmp = fp.read(cdmp_size)

            def cdm(name):
                return ('{http://schemas.microsoft.com/windows/2005/02/color' +
                        '/ColorDeviceModel}' + name)

            def cal(name):
                return ('{http://schemas.microsoft.com/windows/2007/11/color' +
                        '/Calibration}' + name)

            def wcs(name):
                return ('{http://schemas.microsoft.com/windows/2005/02/color' +
                        '/WcsCommonProfileTypes}' + name)

            color_device_model = ET.fromstring(cdmp)

            calibration = color_device_model.find(cdm('Calibration'))

            if calibration is None:
                continue

            adapter_gamma_conf = calibration.find(
                    cal('AdapterGammaConfiguration'))

            if adapter_gamma_conf is None:
                continue

            param_curves = adapter_gamma_conf.find(cal('ParameterizedCurves'))

            if param_curves is not None:
                red_trc = param_curves.find(wcs('RedTRC'))
                green_trc = param_curves.find(wcs('GreenTRC'))
                blue_trc = param_curves.find(wcs('BlueTRC'))

                r_gamma = float(red_trc.get('Gamma'))
                r_gain = float(red_trc.get('Gain', default=1.0))
                r_offset1 = float(red_trc.get('Offset1', default=0.0))
                r_offset2 = float(red_trc.get('Offset2', default=0.0))
                r_offset3 = float(red_trc.get('Offset3', default=0.0))
                r_trnspt = float(red_trc.get('TransitionPoint', default=0.0))
                g_gamma = float(green_trc.get('Gamma'))
                g_gain = float(green_trc.get('Gain', default=1.0))
                g_offset1 = float(green_trc.get('Offset1', default=0.0))
                g_offset2 = float(green_trc.get('Offset2', default=0.0))
                g_offset3 = float(green_trc.get('Offset2', default=0.0))
                g_trnspt = float(green_trc.get('TransitionPoint', default=0.0))
                b_gamma = float(blue_trc.get('Gamma'))
                b_gain = float(blue_trc.get('Gain', default=1.0))
                b_offset1 = float(blue_trc.get('Offset1', default=0.0))
                b_offset2 = float(blue_trc.get('Offset2', default=0.0))
                b_offset3 = float(blue_trc.get('Offset3', default=0.0))
                b_trnspt = float(blue_trc.get('TransitionPoint', default=0.0))

                def curve(gamma, gain, offset1, offset2, offset3, trnspt):
                    if trnspt > 0:
                        y = pow(gain * trnspt + offset1, gamma) + offset2
                        lin_gain = (y - offset3) / trnspt

                        def c(x):
                            if x > trnspt:
                                return pow(gain * x + offset1, gamma) + offset2

                            return lin_gain * x + offset3
                    elif gain > 0:
                        d = -offset1 / gain

                        def c(x):
                            if x > d:
                                return pow(gain * x + offset1, gamma) + offset2

                            return offset2
                    else:
                        def c(x):
                            return offset2

                    return c

                r_curve = curve(r_gamma, r_gain, r_offset1, r_offset2,
                                r_offset3, r_trnspt)
                g_curve = curve(g_gamma, g_gain, g_offset1, g_offset2,
                                g_offset3, g_trnspt)
                b_curve = curve(b_gamma, b_gain, b_offset1, b_offset2,
                                b_offset3, b_trnspt)

                r_ramp = [r_curve(i / (size - 1)) for i in range(size)]
                g_ramp = [g_curve(i / (size - 1)) for i in range(size)]
                b_ramp = [b_curve(i / (size - 1)) for i in range(size)]

                ramp = (r_ramp, g_ramp, b_ramp)
            else:
                hdr_curves = adapter_gamma_conf.find(
                        cal('HDRToneResponseCurves'))

                trc_length = hdr_curves.get('TRCLength')

                red_trc = hdr_curves.find(wcs('RedTRC'))
                green_trc = hdr_curves.find(wcs('GreenTRC'))
                blue_trc = hdr_curves.find(wcs('BlueTRC'))

                r_ramp_x = red_trc.get(wcs('Input')).text.split()
                r_ramp = red_trc.get(wcs('Output')).text.split()
                g_ramp_x = green_trc.get(wcs('Input')).text.split()
                g_ramp = green_trc.get(wcs('Output')).text.split()
                b_ramp_x = blue_trc.get(wcs('Input')).text.split()
                b_ramp = blue_trc.get(wcs('Output')).text.split()

                ramp = (r_ramp, g_ramp, b_ramp)
                ramp_x = [r_ramp_x, g_ramp_x, b_ramp_x]

                assert all(len(x) == trc_length for x in (ramp_x + ramp))

            break

        if tag_name == MLUT:
            fp.seek(tag_offset)

            array = unpack('768H', fp)

            r_ramp = [array[i] / 65535 for i in range(256)]
            g_ramp = [array[i + 256] / 65535 for i in range(256)]
            b_ramp = [array[i + 512] / 65535 for i in range(256)]

            ramp = (r_ramp, g_ramp, b_ramp)
        elif tag_name == VCGT:
            fp.seek(tag_offset)

            tag_type, _, gamma_type = unpack('III', fp)

            assert tag_type == VCGT
            assert gamma_type in (0, 1)

            if gamma_type == 0:
                num_channels, num_entries, entry_size = unpack('HHH', fp)

                if tag_size == 1584:
                    entry_size = 2
                    num_entries = 256
                    num_channels = 3

                assert num_channels == 3
                assert entry_size in (1, 2)

                array = unpack(str(num_entries * 3) + 'BH'[entry_size - 1], fp)

                entry_size = pow(256, entry_size) - 1

                r_ramp = [array[i] / entry_size for i in range(num_entries)]
                g_ramp = [array[i + 256] / entry_size
                          for i in range(num_entries)]
                b_ramp = [array[i + 512] / entry_size
                          for i in range(num_entries)]
            else:
                array = unpack('9I', fp)

                gamma_mult = 2.2 if system == 'Windows' else 1.0

                r_gamma = array[0] / 65536 * gamma_mult
                r_min = array[1] / 65536
                r_max = array[2] / 65536
                g_gamma = array[3] / 65536 * gamma_mult
                g_min = array[4] / 65536
                g_max = array[5] / 65536
                b_gamma = array[6] / 65536 * gamma_mult
                b_min = array[7] / 65536
                b_max = array[8] / 65536

                r_ramp = [pow(i / (size - 1), r_gamma) * (r_max - r_min)
                          + r_min for i in range(size)]
                g_ramp = [pow(i / (size - 1), g_gamma) * (g_max - g_min)
                          + g_min for i in range(size)]
                b_ramp = [pow(i / (size - 1), b_gamma) * (b_max - b_min)
                          + b_min for i in range(size)]

            ramp = (r_ramp, g_ramp, b_ramp)

    if ramp is None:
        ramp = [[i / (size - 1) for i in range(size)] for _ in range(3)]

    ramp_size = len(ramp[0])

    if ramp_x is None:
        ramp_x = [[i / (ramp_size - 1) for i in range(ramp_size)]
                  for _ in range(3)]

    def interpolate(ramp_x, ramp, x):
        i = 0

        while i < ramp_size:
            if x < ramp_x[i]:
                break

            i += 1

        if i == 0:
            return ramp[0]

        if i == ramp_size:
            return ramp[-1]

        x1 = ramp_x[i - 1]
        x2 = ramp_x[i]
        y1 = ramp[i - 1]
        y2 = ramp[i]

        dx = x2 - x1
        dy = y2 - y1

        return y1 + dy * (x - x1) / (dx * dx)

    ramp = [[interpolate(ramp_x[i], ramp[i], j / (size - 1))
             for j in range(size)] for i in range(3)]

    for i in range(3):
        ramp[i][0] = min(max(ramp[i][0], 0.0), 1.0)

        for j in range(1, size):
            ramp[i][j] = min(max(ramp[i][j], ramp[i][j - 1]), 1.0)

    return ramp
