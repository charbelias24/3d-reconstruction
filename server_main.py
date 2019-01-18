# THIS IS THE REFACTORED CODE OF THE PREVIOUS RUNNING FILE ON MASTER RPI

import socket
import time
import os
import RPi.GPIO as GPIO
from picamera import PiCamera
from led import Led



class Server:
    def __init__(self, send_ply_to_laptop=True):
        
        port = 5002
        host_ip = "22.22.22.22"
        red_led_pin = 11
        green_led_pin = 13

        self.send_ply_to_laptop = send_ply_to_laptop

        self.server_image_prefix = 'left'
        self.client_image_prefix = 'right'
        self.ply_prefix = 'pointcloud'

        self.image_path = 'test_images/'
        self.calibration_folder = 'calibration_data_v3/'
        self.ply_path = 'ply_output/'

        self.image_count = ''
        self.image_extension = '.jpg'
        self.ply_extension = '.ply'
        self.rpi_client_address = '22.22.22.23'

        self.red_led = Led(red_led_pin)
        self.green_led = Led(green_led_pin)

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.client_socket = 0
        self.laptop_socket = 0

        try:
            self.camera = PiCamera()
            self.camera.resolution = (640, 480)

            self.server_socket.bind((host_ip, port))
            self.server_socket.listen(5)

            self.chunk_size = 1024
            
            print("HOST IS ONLINE: {}:{}".format(host_ip, port))



        except Exception as e:
            print(e)
            self.red_led.blink(2, 0.2)
            # del self ## TEST THIS LINE

    def __del__(self):
        if self.client_socket:
            self.client_socket.close()
        if self.laptop_socket:
            self.laptop_socket.close()
        self.server_socket.close()
        self.camera.close()
        print("CLOSED CONNECTION SECURELY")

    @property
    def add_count_to_image_name(self):
        return self.client_image_prefix + self.image_count, self.server_image_prefix + self.image_count

    def get_img_count(self):
        try:
            with open('data/current_count.txt', 'r') as file:
                current_count = file.read()
                if current_count:
                    current_count = int(current_count)

            with open('data/current_count.txt', 'w') as file:
                file.write(str(current_count + 1))

            self.image_count = str(current_count)

        except Exception as e:
            print(e)

    def take_picture(self, server_image_name):
        self.camera.capture(self.image_path + server_image_name + self.image_extension)
        print("IMAGE SAVED IN: {}".format(self.image_path + server_image_name + self.image_extension))
   
    def send_count(self):
        self.client_socket.send(self.image_count)
        # print("SENDING IMAGE COUNT")
        reply = self.client_socket.recv(1024)
        if reply == "RECEIVED":
            # print("THE CLIENT GOT THE COUNT")
            return 1
        else:
            # print("THE CLIENT DID NOT GET THE COUNT")
            return 0

    def receive_image(self, client_image_name):
        # print("WAITING FOR CLIENT TO SEND DATA")
        data = self.client_socket.recv(1024)
        image_full = self.image_path + client_image_name + self.image_extension

        if data.split(' ')[0] == 'SIZE':
            # img_size = int(data.split(' ')[1])
            # print("GOT SIZE: {}".format(img_size))
            self.client_socket.send("GOT SIZE")

            with open(image_full, 'wb') as img:
                while True:
                    chunk_data = self.client_socket.recv(self.chunk_size)
                    if "DONE" in chunk_data:
                        img.write(chunk_data[:-4])
                        break
                    img.write(chunk_data)
        self.client_socket.send("IMAGE RECEIVED")
        print("IMAGE SAVED IN: {}".format(image_full))

    def send_ply(self):
        ply_name = self.ply_path + self.ply_prefix + self.image_count + self.ply_extension

        with open(ply_name, 'rb') as ply_file:
            image_bytes = ply_file.read()

            self.laptop_socket.send(image_bytes)
            self.laptop_socket.send("DONE")

        reply = self.client_socket.recv(1024)
        if reply == "FILE RECEIVED":
            print("POINT CLOUD SENT SUCCESSFULLY")
            return 1
        else:
            print("ERROR SENDING POINT CLOUD")
            return 0

    def connect_clients(self):
        # if the ply should be send to the laptop
        # the rpi and the laptop should be connected at first
        if self.send_ply_to_laptop:
            while not (self.client_socket and self.laptop_socket):
                temp_socket, temp_address = self.server_socket.accept()

                if str(temp_address[0]) == self.rpi_client_address:
                    self.client_socket = temp_socket
                else:
                    self.laptop_socket = temp_socket

        else:
            self.client_socket, address = self.server_socket.accept()
            print("CONNECTED TO: " + str(address[0]))

    def run(self):
        self.get_img_count()
        client_image_name, server_image_name = self.add_count_to_image_name
        self.send_count()
        self.green_led.turn_on()
        self.take_picture(server_image_name)
        self.receive_image(client_image_name)
        self.green_led.turn_off()
        if self.send_ply_to_laptop:
            os.system("images_to_pointcloud {} {} {} {}".format(self.calibration_folder,
                                                            self.image_path + server_image_name + self.image_extension,
                                                            self.image_path + client_image_name + self.image_extension,
                                                            self.ply_extension + self.ply_prefix + self.image_count + self.ply_extension))
            self.send_ply()

        print('\n')


def main():
    btn_pin = 7
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(btn_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setwarnings(False)
    server = Server()

    try:
        while True:
            if GPIO.input(btn_pin):  # Checking if the button is pressed
                print("BUTTON PRESSED")
                server.run()
                time.sleep(0.5)
            time.sleep(0.01)

    except Exception as e:
        server.red_led.blink(2, 0.2)
        print(e)

    finally:
        del server


if __name__ == "__main__":
    main()
