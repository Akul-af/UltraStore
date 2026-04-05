import os
import cv2
import numpy as np
import struct
import tempfile
import subprocess
import shutil

def encode_to_lossless_mkv(filename, output_name="output.mkv", frame_dim=512, framerate=1):
    """
    Encode an arbitrary file into a lossless MKV using FFV1.
    - Reserves 12 bytes in the first frame for metadata: 4 bytes filesize (big-endian) + 8 bytes extension.
    - Writes frames as PNG (lossless) then packs them into an FFV1 MKV via ffmpeg.
    Requires ffmpeg on PATH.
    """
    # Read file
    with open(filename, "rb") as f:
        data = f.read()
    filesize = len(data)
    extension = os.path.splitext(filename)[1] or ""
    # Prepare metadata
    size_bytes = struct.pack(">I", filesize)
    ext_bytes = extension.encode("utf-8")[:8].ljust(8, b"\x00")
    metadata = size_bytes + ext_bytes  # 12 bytes

    frame_size = frame_dim * frame_dim
    first_capacity = frame_size - 12
    # Create temp dir for frames
    tmpdir = tempfile.mkdtemp(prefix="frames_")
    try:
        offset = 0
        frame_index = 0
        while offset < len(data) or frame_index == 0:
            if frame_index == 0:
                chunk = data[offset:offset + first_capacity]
                offset += len(chunk)
                flat = np.zeros(frame_size, dtype=np.uint8)
                flat[:12] = np.frombuffer(metadata, dtype=np.uint8)
                if len(chunk) > 0:
                    flat[12:12+len(chunk)] = np.frombuffer(chunk, dtype=np.uint8)
            else:
                chunk = data[offset:offset + frame_size]
                offset += len(chunk)
                padded = np.pad(np.frombuffer(chunk, dtype=np.uint8), (0, frame_size - len(chunk)), 'constant')
                flat = padded
            frame = flat.reshape((frame_dim, frame_dim))
            fname = os.path.join(tmpdir, f"frame_{frame_index:06d}.png")
            # Save grayscale PNG (lossless)
            cv2.imwrite(fname, frame)
            frame_index += 1
            if len(chunk) == 0 and frame_index > 1:
                break

        # Pack PNG sequence into lossless FFV1 MKV using ffmpeg
        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(framerate),
            "-i", os.path.join(tmpdir, "frame_%06d.png"),
            "-c:v", "ffv1", "-level", "3", "-g", "1",
            output_name
        ]
        subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    finally:
        # cleanup temp frames
        try:
            shutil.rmtree(tmpdir)
        except Exception:
            pass

    print(f"Encoding complete: {output_name} ({frame_index} frames)")

def decode_from_lossless_mkv(video_name="output.mkv", output_file=None, frame_dim=512):
    """
    Decode a file encoded with encode_to_lossless_mkv.
    - Reads first 12 bytes from first frame for filesize and extension.
    - Concatenates frame data, trims to filesize, writes output.
    """
    cap = cv2.VideoCapture(video_name)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_name}")

    all_bytes = bytearray()
    frame_index = 0
    filesize = None
    extension = None

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        # Ensure single-channel grayscale
        if frame.ndim == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame
        flat = gray.flatten()

        if frame_index == 0:
            # Extract metadata
            filesize = struct.unpack(">I", flat[:4].tobytes())[0]
            extension = flat[4:12].tobytes().decode("utf-8").rstrip("\x00")
            all_bytes.extend(flat[12:].tobytes())
        else:
            all_bytes.extend(flat.tobytes())

        frame_index += 1

    cap.release()

    if filesize is None:
        raise RuntimeError("No frames found or metadata missing.")

    # Trim to original size
    all_bytes = all_bytes[:filesize]

    if output_file is None:
        output_file = "decoded_file" + (extension or "")

    with open(output_file, "wb") as f:
        f.write(all_bytes)

    print(f"Decoding complete: {output_file} ({len(all_bytes)} bytes)")

while True:
    print(os.getcwd())
    print("Do you want to change directory (y/n)")
    change = input()
    change = change.lower().strip()
    m = ".mkv"
    if change == "y":
        print("Enter directory")
        directory = input()
        try:
            os.chdir(directory)
        except:
            print("It seems that the path may have been wrong,please enter the correct path")
        print(os.getcwd())
        print("Do you want to encode or decode(e/d)")
        d = input()
        d = d.lower().strip()
        if d == "e":
            print("Enter file name with . extension name")
            x = input()
            try:
                name = open(x,"rb")
            except:
                print("It seems your filename and/or the .extension might have been entered wrong")
            data = name.read()
            name.close()
            encode_to_lossless_mkv(x,x+m,512)
            print(f"Encode as {x+m}")
        else:
            print("Enter the full video name")
            g = input()
            print("Enter the full output name")
            c = input()
            try:
                fame = open(g,"rb")
            except:
                print("It seems your video name might have been wrong please try again")
            mata = fame.read()
            fame.close()
            decode_from_lossless_mkv(g,c,512)
            print(f"Decode as {c}")
    else:
        print("Do you want to encode or decode(e/d)")
        d = input()
        d = d.lower().strip()
        if d == "e":
            print("Enter file name with . extension name")
            x = input()
            try:
                name = open(x,"rb")
            except:
                print("It seems your filename and/or the .extension might have been entered wrong")
            data = name.read()
            name.close()
            encode_to_lossless_mkv(x,x+m,512)
            print(f"Encode as {x+m}")
        else:
            print("Enter the full video name")
            g = input()
            print("Enter the full output name")
            c = input()
            try:
                fame = open(g,"rb")
            except:
                print("It seems your video name might have been wrong please try again")
            mata = fame.read()
            fame.close()
            decode_from_lossless_mkv(g,c,512)
            print(f"Decode as {c}")


