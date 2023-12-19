import subprocess
import os
import time
import threading
import socketio
import base64
import keyboard
from io import BytesIO
from PIL import Image
from tkinter import filedialog
import tkinter as tk

# Socket io server address
SOCKETIO_SERVER_ADDR = 'http://oracle-api.rjrietdijk.com'
# Print settings
DPI = 300
W_IN = 4
H_IN = 6


def execute_command(command):
    def monitor_process(proc):
        while True:
            output = proc.stdout.readline()
            if output == '':
                if proc.poll() is not None:
                    break
            else:
                print(output.strip().decode())

        rc = proc.poll()
        print(f"Process exited with code {rc}")

    process = subprocess.Popen(
        command, 
        shell=True, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.STDOUT
    )

    # Start a thread to monitor stdout/stderr
    monitor_thread = threading.Thread(target=monitor_process, args=(process,))
    monitor_thread.start()

    # While the process is running, print periodic messages
    while process.poll() is None:
        print("Printing in progress...")
        time.sleep(1)

    monitor_thread.join()  # Wait for the monitoring thread to finish

def select_irfanview_executable():
    root = tk.Tk()
    root.withdraw()  # Hides the small tkinter window

    file_path = filedialog.askopenfilename(
        title="Select IrfanView Executable (i_view64.exe)",
        filetypes=[("Executable Files", "*.exe")]
    )

    if file_path:
        return file_path
    else:
        return None

irfanview_path = select_irfanview_executable()

if irfanview_path and os.path.isfile(irfanview_path):
    print(f"IrfanView executable selected: {irfanview_path}")
else:
    print("IrfanView executable not selected or not found.")


def on_key_event(e):
    if e.name == 'q':
        print("Closing connection...")
        sio.disconnect()
        exit()

def resize_and_crop(image, output_path, page_dimensions):
    try:
        # Resize for best fit
        image.thumbnail(page_dimensions, Image.Resampling.LANCZOS)

        # Calculate dimensions to fill the page
        page_ratio = page_dimensions[0] / page_dimensions[1]
        img_ratio = image.width / image.height

        if img_ratio > page_ratio:
            # Image is wider than the destination ratio
            new_height = page_dimensions[1]
            new_width = int(new_height * img_ratio)
        else:
            # Image is taller than the destination ratio
            new_width = page_dimensions[0]
            new_height = int(new_width / img_ratio)

        img_resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Crop to fill the page
        left = (new_width - page_dimensions[0]) / 2
        top = (new_height - page_dimensions[1]) / 2
        right = (new_width + page_dimensions[0]) / 2
        bottom = (new_height + page_dimensions[1]) / 2

        img_cropped = img_resized.crop((left, top, right, bottom))

        # Save the final image
        img_cropped.save(output_path, quality=95)
    
    except Exception as e:
        print(f"An error occurred: {e}")

def preprocess_print(image, output_image_path):
    page_size = (W_IN * DPI, H_IN * DPI)
    resize_and_crop(image, output_image_path, page_size)

def process_print(output_image_path):
    # Construct the command to print the image
    # Additional command-line options can be added for more specific print settings
    command = f'"{irfanview_path}" "{output_image_path}" /dpi=({DPI},{DPI}) /print'

    # Execute the command
    execute_command(command)

sio = socketio.Client()

@sio.event
def connect():
    print("Connected to server")

@sio.event
def disconnect():
    print("Disconnected from server")

@sio.on('print')
def print_image(data):
    try:
        image_data_url = data['image']
        current_directory = os.path.dirname(os.path.abspath(__file__))
        output_image_path = os.path.join(current_directory, 'print_processed.jpg')

        # Decode the image data URL
        header, encoded = image_data_url.split(",", 1)
        image_data = base64.b64decode(encoded)

        # Create an Image object from the decoded data
        with Image.open(BytesIO(image_data)) as image:
            # Preprocess and print the image
            preprocess_print(image, output_image_path)

        process_print(output_image_path)
    except KeyError:
        print("Error: Missing data in print event")

sio.connect(SOCKETIO_SERVER_ADDR)
keyboard.on_press(on_key_event)
sio.emit('printer_connect') 
sio.wait()