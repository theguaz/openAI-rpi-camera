import base64
import requests
import os
import picamera
import time
import os
import datetime
import uuid
import subprocess

import random

#create your config accordingly:
#api_key = "your_api_key_here"
#elevenLabsAPiKey = "your_elevenLabs_api_key_here"
#voice_id = "your_voice_id_here"
from playsound import playsound


import config
import RPi.GPIO as GPIO
import sys

from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont

import openai
from elevenlabs import generate, play, stream, voices, save
from elevenlabs import set_api_key

msgs = ["sht", "ask", "spk", "done"]

client_process = None


# OpenAI API Key

api_key = config.api_key
elevenLabsAPiKey = config.elevenLabsAPiKey
voice_id = config.voice_id

isProcessing = False


start_time = 0


projectFolder = '/home/pi/openAI-rpi-11labs-test/'

set_api_key(elevenLabsAPiKey)

thePrompt = "You're a character from a Guy Ritchie movie, you describe by creating a rhyme in shakespearerian style what you see on the image taken by the device it contains you. Take into account common sense and always stay respectful. You're reviewing images from your own point of view, answer as you were browsing social media. \n\nYou'll receive images one at a time, \n\nYou'll never answer with a question, this is a one time conversation with you\n\n It's very important that you begin each answer with a variation of this: \n 'Ok, this is what I see on the image ' "


def select_random_phrase():
    analysisPhrases = [
        "Analyzing image details...",
        "Decoding visual data...",
        "Interpreting the pixels...",
        "Rendering insights...",
        "Examining the snapshot...",
        "Unpacking image content...",
        "Image analysis underway...",
        "Breaking down the picture...",
        "Reading visual information...",
        "Fetching image details...",
        "Extracting data from image...",
        "Converting image to insights...",
        "Processing visual input...",
        "Scanning image content...",
        "Evaluating pictorial elements...",
        "Assessing image composition...",
        "Compiling image analysis...",
        "Deriving insights from image...",
        "Crunching image data...",
        "Dissecting the frame..."
    ]
    # Select a random phrase from the list
    return random.choice(analysisPhrases)

# Function to encode the image
def encode_image(image_path):
  with open(image_path, "rb") as image_file:
    return base64.b64encode(image_file.read()).decode('utf-8')

def save_log(message):
    with open("log.txt", "a") as log_file:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_file.write(f"{timestamp} - {message}\n")

def write_text_on_image(image_path, text, position=(10, 10), font_size=5, font_color="white"):

    try:
        # Open the image
        with Image.open(image_path) as img:
            # Create a drawing context
            draw = ImageDraw.Draw(img)

            # Load a font
            #font = ImageFont.truetype("arial.ttf", font_size)

            # Add text to image
            draw.text(position, text, fill=font_color)

            # Save the image
            img.save(image_path)

    except IOError as e:
        print(f"Error opening or processing the image: {e}")

def getImageInfo(image_path):
    base64_image = encode_image(image_path)
    print("asking open ai for --->", {image_path})
    headers = {
      "Content-Type": "application/json",
      "Authorization": f"Bearer {api_key}"
    }
    payload = {
      "model": "gpt-4-vision-preview",
      "messages": [
        {
          "role": "user",
          "content": [
            {
              "type": "text",
              "text": thePrompt
            },
            {
              "type": "image_url",
              "image_url": {
                "url": f"data:image/jpeg;base64,{base64_image}"
              }
            }
          ]
        }
      ],
      "max_tokens": 1024
    }
    openAI_response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    print(openAI_response.json())
    msg = openAI_response.json()
    return msg['choices'][0]['message']['content']

def create_video_from_image_and_audio(image_path, audio_path, output_video_path):
    try:
        command = [
            'ffmpeg',
            '-loop', '1',
            '-framerate', '1',
            '-i', image_path,
            '-i', audio_path,
            '-c:v', 'libx264',
            '-tune', 'stillimage',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-shortest',
            '-pix_fmt', 'yuv420p',
            output_video_path
        ]

        subprocess.run(command, check=True)
        print(f"Video created successfully: {output_video_path}")
    except subprocess.CalledProcessError as e:
        print(f"Error occurred: {e}")

def capture_image(uuidID, save_dir="/home/pi/openAI-rpi-11labs-test/captures"):
    # Ensure the save directory exists
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    # Create a file name based on the current time
    file_name = uuidID + ".jpg"
    file_path = os.path.join(save_dir, file_name)

    # Capture the image
    with picamera.PiCamera() as camera:
        camera.resolution = (1280, 720)  # You can adjust the resolution
        camera.hflip = True
        camera.rotation = 90
        camera.start_preview()
        # Camera warm-up time
        print("warming camera")
        time.sleep(.25)
        camera.capture(file_path)
        print(f"Image captured and saved as {file_path}")

    return file_path

def process_image(filename, uuidID):
  info = getImageInfo(filename)
  
  logInfo = filename + " ---> " + info + "\n\n"
  write_text_on_image(filename, logInfo)
  save_log(logInfo)
  print("generating audio with elevenLabs")
  audiogen = generate(text =  info, voice=voice_id)

  nameOf = uuidID
  
  input_audio_path = projectFolder + "audios/" + nameOf + '_answer.wav'
  print("playing msg \n\n")
  print("saving msg \n\n")
  save(audiogen, input_audio_path )
  
  return info , input_audio_path, audiogen


def justTalk(str):
  audiogen = generate(text =  str, voice=voice_id)
  print(f"playing {str} \n\n")
  play(audiogen)


def simpleMSG(thePrompt):
    headers = {
      "Content-Type": "application/json",
      "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [
          {
            "role": "user",
            "content": [
              {
                "type": "text",
                "text": thePrompt
              }
            ]
          }
        ],
        "max_tokens": 32
      }
    openAI_response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    msg = openAI_response.json()
    return msg['choices'][0]['message']['content']

def triggered_function():

  playsound('/home/pi/openAI-rpi-11labs-test/shutter.wav')
  

  start_time = time.time()
  isProcessing = True
  print("shooting....")


  uuidID = str( uuid.uuid4() )
  
  captured_image_path = capture_image(uuidID)

  justTalk( select_random_phrase() )

  process = process_image(captured_image_path, uuidID)
  
  #create_video_from_image_and_audio(captured_image_path, process[1], 'videos/' + uuidID + ".mp4" )
  
  end_time = time.time()
  elapsed_time = end_time - start_time
  print("task completed for UUID--> " + uuidID + " in exactly " + str(elapsed_time) + " secs")
  
  play(process[2])
  
  isProcessing = False



if __name__ == "__main__":
    print("initializing shakespeare camera")
    justTalk( simpleMSG("Write me a 10 words very short message in cockney english that informs that we are connected to the internet and ready to start shooting photographs") )

    GPIO.setmode(GPIO.BCM)  # Use Broadcom pin numbering
    GPIO.setup(14, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Button to GPIO17
try:
    while True:
      button_state = GPIO.input(14)
      if button_state == False and isProcessing == False:  # Button is pressed
        triggered_function()
        time.sleep(0.05)  # Add a small delay to debounce
except KeyboardInterrupt:
  print("Program stopped by User")
except Exception as e:
  print("An error occurred:", e)
finally:
  GPIO.cleanup()  # This ensures a clean exit
#end