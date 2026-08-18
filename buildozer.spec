[app]

# (str) Title of your application
title = Multi Strategy Signal

# (str) Package name
package.name = multistrategysignal

# (str) Package domain
package.domain = org.multistrategysignal

# (str) Source code directory
source.dir = .

# (str) Application entry point
# app.py will be used as the main Python file

# (str) Source files to include
source.include_exts = py,png,jpg,jpeg,kv,atlas,json

# (str) Application version
version = 1.0

# (str) Python requirements
requirements = python3,kivy,requests,pandas,numpy

# (str) Portrait mode
orientation = portrait

# (bool) Fullscreen
fullscreen = 0

# (str) Presplash
# presplash.filename = %(source.dir)s/data/presplash.png

# (str) Icon
# icon.filename = %(source.dir)s/data/icon.png

# (str) Supported Android architectures
android.archs = arm64-v8a,armeabi-v7a

# (str) Android API
android.api = 33

# (str) Minimum Android API
android.minapi = 24

# (str) Android permissions
android.permissions = INTERNET

# (str) Android private storage
android.private_storage = True

# (str) Android window
android.wakelock = 0

# (bool) Allow Android backup
android.allow_backup = True

# (str) Logcat filters
android.logcat_filters = *:S python:I pythonforandroid:I

# (str) Android application activity
android.entrypoint = org.kivy.android.PythonActivity

# (str) Python for Android bootstrap
p4a.bootstrap = sdl2

# (str) Android SDL2
p4a.branch = master

# (str) Extra p4a arguments
p4a.extra_args = --color=always

# (bool) Show console
android.add_src =

# (str) Android launch mode
android.launch_mode = standard

# (str) Android orientation
android.orientation = portrait


[buildozer]

# (int) Log level
log_level = 2

# (bool) Warn if running as root
warn_on_root = 1
