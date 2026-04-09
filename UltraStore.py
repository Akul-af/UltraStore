import os
import cv2
import numpy as np
import struct
import tempfile
import subprocess
import shutil

def encode_to_lossless_mkv(filename, output_name="output.mkv", framerate=1):
    """
    Encode an arbitrary file into a lossless MKV using FFV1.
    - Reserves 14 bytes in the first frame for metadata:
      4 bytes filesize (big-endian) + 8 bytes extension + 2 bytes frame_dim.
    - Writes frames as PNG (lossless) then packs them into an FFV1 MKV via ffmpeg.
    ffmpeg.exe must be in the same folder as this script/exe.
    """
    # Read file
    with open(filename, "rb") as f:
        data = f.read()
    filesize = len(data)
    extension = os.path.splitext(filename)[1] or ""

    # Dynamic frame dimension based on file size
    if filesize <= 100 * 1024:
        final_dim = 256
    elif filesize <= 6400 * 1024:
        final_dim = 512
    elif filesize <= 102400 * 1024:
        final_dim = 1024
    else:
        final_dim = 2048

    # Prepare metadata (14 bytes total)
    size_bytes = struct.pack(">I", filesize)
    ext_bytes = extension.encode("utf-8")[:8].ljust(8, b"\x00")
    dim_bytes = final_dim.to_bytes(2, byteorder="big")
    metadata = size_bytes + ext_bytes + dim_bytes

    frame_size = final_dim * final_dim
    header_len = 14
    first_capacity = frame_size - header_len

    tmpdir = tempfile.mkdtemp(prefix="frames_")
    try:
        offset = 0
        frame_index = 0
        while offset < len(data) or frame_index == 0:
            if frame_index == 0:
                chunk = data[offset:offset + first_capacity]
                offset += len(chunk)
                flat = np.zeros(frame_size, dtype=np.uint8)
                flat[:14] = np.frombuffer(metadata, dtype=np.uint8)
                if len(chunk) > 0:
                    flat[14:14+len(chunk)] = np.frombuffer(chunk, dtype=np.uint8)
            else:
                chunk = data[offset:offset + frame_size]
                offset += len(chunk)
                padded = np.pad(np.frombuffer(chunk, dtype=np.uint8),
                                (0, frame_size - len(chunk)), 'constant')
                flat = padded
            frame = flat.reshape((final_dim, final_dim))
            fname = os.path.join(tmpdir, f"frame_{frame_index:06d}.png")
            cv2.imwrite(fname, frame)
            frame_index += 1
            if len(chunk) == 0 and frame_index > 1:
                break

        # Use local ffmpeg.exe bundled with exe
        ffmpeg_path = os.path.join(os.path.dirname(__file__), "ffmpeg.exe")
        cmd = [
            ffmpeg_path, "-y",
            "-framerate", str(framerate),
            "-i", os.path.join(tmpdir, "frame_%06d.png"),
            "-c:v", "ffv1", "-level", "3", "-g", "1",
            output_name
        ]
        subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    print(f"Encoding complete: {output_name} ({frame_index} frames)")


def decode_from_lossless_mkv(video_name="output.mkv", output_file=None, frame_dim=512):
    """
    Decode a file encoded with encode_to_lossless_mkv.
    - Reads first 14 bytes from first frame for filesize, extension, and frame_dim.
    - Concatenates frame data, trims to filesize, writes output.
    """
    cap = cv2.VideoCapture(video_name)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_name}")

    all_bytes = bytearray()
    frame_index = 0
    filesize = None
    extension = None
    forced_frame_dim = None

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
        flat = gray.flatten()

        if frame_index == 0:
            filesize = struct.unpack(">I", flat[:4].tobytes())[0]
            extension = flat[4:12].tobytes().decode("utf-8").rstrip("\x00")
            possible_dim = int.from_bytes(flat[12:14].tobytes(), byteorder="big")
            if possible_dim in (256, 512, 1024, 2048):
                forced_frame_dim = possible_dim
                frame_dim = forced_frame_dim
            all_bytes.extend(flat[14:].tobytes())
        else:
            all_bytes.extend(flat.tobytes())

        frame_index += 1

    cap.release()

    if filesize is None:
        raise RuntimeError("No frames found or metadata missing.")

    all_bytes = all_bytes[:filesize]

    if output_file is None:
        output_file = "decoded_file" + (extension or "")

    with open(output_file, "wb") as f:
        f.write(all_bytes)

    print(f"Decoding complete: {output_file} ({len(all_bytes)} bytes)")


def main():
    while True:
        print(os.getcwd())
        change = input("Do you want to change directory (y/n): ").lower().strip()
        m = ".mkv"
        if change == "y":
            directory = input("Enter directory: ")
            try:
                os.chdir(directory)
            except:
                print("Invalid path, please try again.")
                continue

        d = input("Do you want to encode or decode (e/d): ").lower().strip()
        if d == "e":
            x = input("Enter file name with extension: ")
            try:
                with open(x, "rb") as name:
                    data = name.read()
            except:
                print("Invalid filename or extension.")
                continue
            encode_to_lossless_mkv(x, x+m, 1)
            print(f"Encoded as {x+m}")
        elif d == "d":
            g = input("Enter the full video name: ")
            c = input("Enter the full output name: ")
            try:
                with open(g, "rb") as fame:
                    mata = fame.read()
            except:
                print("Invalid video name, please try again.")
                continue
            decode_from_lossless_mkv(g, c, 512)
            print(f"Decoded as {c}")


if __name__ == "__main__":
    main()
