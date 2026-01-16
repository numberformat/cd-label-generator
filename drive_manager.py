import win32file
import win32con
import string
import ctypes
import discid

def get_optical_drives():
    drives = []
    bitmask = ctypes.windll.kernel32.GetLogicalDrives()

    for letter in string.ascii_uppercase:
        if bitmask & 1:
            drive = f"{letter}:"
            try:
                drive_type = win32file.GetDriveType(drive)
                if drive_type == win32con.DRIVE_CDROM:
                    drives.append(drive)
            except:
                pass
        bitmask >>= 1

    return drives

def eject_cd(drive_letter):
    drive = drive_letter.rstrip(":")
    cmd = f"open {drive}: type CDAudio alias drive"
    ctypes.windll.winmm.mciSendStringW(cmd, None, 0, None)
    ctypes.windll.winmm.mciSendStringW("set drive door open", None, 0, None)
    ctypes.windll.winmm.mciSendStringW("close drive", None, 0, None)


def get_current_disc_id(drive):
    try:
        disc = discid.read(drive)
        return disc.id
    except:
        return None
    
def print_track_durations(drive, print_func=print):
    try:
        disc = discid.read(drive)
        print_func("\nTrack list (for identification):")
        print_func("---------------------------------")

        for i, t in enumerate(disc.tracks, start=1):
            seconds = t.length // 75
            mm = seconds // 60
            ss = seconds % 60
            print_func(f"{i:2d}. {mm:02d}:{ss:02d}")

        print_func("---------------------------------")
        print_func("Use this + artist/album to search on https://musicbrainz.org\n")

    except Exception as e:
        print_func(f"Failed to read track durations: {e}")