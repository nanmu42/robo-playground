# RoboMasterPy Playground

**English** | [中文](https://github.com/nanmu42/robo-playground/blob/master/README.Chinese.md)

[![Documentation Status](https://readthedocs.org/projects/robomasterpy/badge/?version=latest)](https://robomasterpy.nanmu.me/en/latest/?badge=latest)
[![](https://img.shields.io/pypi/l/robomasterpy.svg)](https://pypi.org/project/robomasterpy/)
[![](https://img.shields.io/pypi/wheel/robomasterpy.svg)](https://pypi.org/project/robomasterpy/)
[![](https://img.shields.io/pypi/pyversions/robomasterpy.svg)](https://pypi.org/project/robomasterpy/)

Games and examples built for [RoboMaster EP](https://en.wikipedia.org/wiki/RoboMaster#RoboMaster_EP) with [RoboMasterPy](https://github.com/nanmu42/robomasterpy).

![RoboMasterPy Goalkeeper](https://user-images.githubusercontent.com/8143068/82755582-186d5700-9e07-11ea-9c08-1ff1d82e7a7e.jpg)

## 开始游戏

RoboMasterPy Playground requires Python 3.6 and above.

```bash
# optional, suggested
virtualenv venv

# Python 3.6.x
pip install -r requirements-py36.txt
# Python 3.7 and above
pip install -r requirements.txt
```

### Drive your robomaster using keyboard

Live video stream is displayed on your screen.

```bash
$ python drive.py --help
Usage: drive.py [OPTIONS]

Options:
  --ip TEXT        (Optional) IP of Robomaster EP
  --timeout FLOAT  (Optional) Timeout for commands
  --help           Show this message and exit.
```

Key bindings:

* `W`, `A`, `S`, `D`: forward, leftward, backward, rightward;
* `space bar`: blaster fire
* `up`, `down`: gimbal pitch up, gimbal pitch down
* `left`, `right`: chassis roll left, chassis roll right
* `1`~`5`: gears

### Make your robomaster a goalkeeper

You need tweak `GREEN_LOWER` and `GREEN_UPPER` per your luminance to get good experience. The default values works okay under daylight shade.

```bash
$ python goalkeeper.py --help
Usage: goalkeeper.py [OPTIONS]

Options:
  --ip TEXT          (Optional) IP of Robomaster EP
  --timeout FLOAT    (Optional) Timeout for commands
  --max-width FLOAT  (Optional) Field width
  --max-depth FLOAT  (Optional) Field depth
  --xy-speed FLOAT   (Optional) Speed in x and y direction
  --z-speed FLOAT    (Optional) Speed in z direction(chassis roll)
  --help             Show this message and exit.
```

## RoboMasterPy User Guide

https://robomasterpy.nanmu.me/

Documentation is generously hosted by Read the Docs.

## Health and Safety Notice

* Your Robomaster may hurt people or pet, break stuffs or itself;
* Make sure your RoboMaster has enough room to move; make sure the ground is clear;
* Start slowly, avoid using high speed for debugging;
* Use cushion;
* Stay safe and have fun!

## Paperwork

RoboMasterPy Playground is a fan work, and it has no concern with DJI.

DJI, RoboMaster are trademarks of SZ DJI Technology Co., Ltd.

## Acknowledgement

RoboMasterPy Playground was incubated during a RoboMaster EP developing contest. The author would like to thank DJI for hardware and technical support.

## License

RoboMasterPy Playground is released under MIT license.