# RustServerManager for Windows
A tool designed to Install, Update, Auto start RUST servers!

RustServerManager is a extremely light-weight, simplistic & efficient Wrapper for RUST servers hosted on Windows.

Requirements:
  - Python 3.9+
  - Python added to system path

Features:
  - Auto install (Game files, Oxide, Rust Edit).
  - Auto update (Game files, Oxide, Rust Edit).
  - Crash restart.

Installation:
  - Download latest release
  - Run the `start.bat`
  - Configure server settings (check configuration bellow)
  - Thats it, really!
 
Configuration:
  - Server start parameters can be edited inside 'rust_data/config.cfg'
  - For auto restarts i recommend https://umod.org/plugins/smooth-restarter
  - If you are running vanilla (community) server make sure to set 'modded' to false inside oxide config!
 
Troubleshooting:
  - Nothing happened after launching start.bat, 
     - run app.py using cmd with `python app.py` if there is an error: `'python' is not recognised as an internal or external command` you haven't set up python path                properly. Watch for fix: https://www.youtube.com/watch?v=4bUOrMj88Pc&t=351s

Note: This project is in no way affiliated with the one being sold out there.
