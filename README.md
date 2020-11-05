# zzzmachine

The more you sleep, the more you learn.

## Introduction

This script automates the recording of online lectures and uploads the recordings to a Google Drive account, so you can watch them when you wake up.

## Requriments
The scirpt is developed for Linux machines.
It reqiures:
  * Selenium: https://www.selenium.dev/
  * Chromedriver: https://chromedriver.chromium.org/
  * FFmpeg: https://ffmpeg.org/
  * Pavucontrol: https://launchpad.net/ubuntu/+source/pavucontrol
  * Pydrive library: https://pythonhosted.org/PyDrive/
  
## Installation
 
1. Install selenium, chromedriver, ffmpeg, pavucontrol and pydrive.
2. Then follow the instructions described in the following articles:
   * https://itectec.com/ubuntu/ubuntu-capturing-only-desktop-audio-with-ffmpeg/
   * https://medium.com/analytics-vidhya/how-to-connect-google-drive-to-python-using-pydrive-9681b2a14f20
3. After that, run *database_initializer.py* in order to create **myschedule.db**
4. Finally insert your schedule in **myschedule.db** and run *recorder.py*
