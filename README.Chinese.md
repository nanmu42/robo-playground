# RoboMasterPy Playground

[English]((https://github.com/nanmu42/robo-playground/blob/master/README.md)) | **中文**

[![Documentation Status](https://readthedocs.org/projects/robomasterpy/badge/?version=latest)](https://robomasterpy.nanmu.me/en/latest/?badge=latest)
[![](https://img.shields.io/pypi/l/robomasterpy.svg)](https://pypi.org/project/robomasterpy/)
[![](https://img.shields.io/pypi/wheel/robomasterpy.svg)](https://pypi.org/project/robomasterpy/)
[![](https://img.shields.io/pypi/pyversions/robomasterpy.svg)](https://pypi.org/project/robomasterpy/)

基于[RoboMasterPy](https://github.com/nanmu42/robomasterpy)构建的[机甲大师EP](https://www.dji.com/cn/robomaster-ep)的游戏和范例。

![RoboMasterPy 机甲大师守门员](https://user-images.githubusercontent.com/8143068/82755582-186d5700-9e07-11ea-9c08-1ff1d82e7a7e.jpg)

## 开始游戏

RoboMasterPy Playground 需要 Python 3.6 或更高以运行。

```bash
# 可选，推荐
virtualenv venv

# Python 3.6.x
pip install -r requirements-py36.txt
# Python 3.7 或更高
pip install -r requirements.txt
```

### 使用键盘控制你的机甲大师EP

机甲的视频流会在你的显示器上显示。

```bash
$ python drive.py --help
Usage: drive.py [OPTIONS]

Options:
  --ip TEXT        (Optional) IP of Robomaster EP
  --timeout FLOAT  (Optional) Timeout for commands
  --help           Show this message and exit.
```

操作键位：

* `W`, `A`, `S`, `D`: 前，左，后，右；
* `space bar`: 开火；
* `up`, `down`: 云台抬头，云台低头；
* `left`, `right`: 底盘左转，底盘右转；
* `1`~`5`: 档位。

### 让你的机甲大师EP变身为守门员

你需要根据光照环境调整`GREEN_LOWER`和`GREEN_UPPER`以获得最佳体验。默认值在自然光阴影下工作良好。

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

## RoboMasterPy 用户指南

https://robomasterpy.nanmu.me/

Read the Docs 慷慨地提供了文档托管服务。

## 健康和安全警示

* 你的机甲大师可能会伤到人或者宠物，打破东西或者弄坏自己；
* 确保机甲大师有足够的行动空间，确保地面平整且没有障碍；
* 慢慢来，避免在调试代码时使用高速档位；
* 使用缓冲垫；
* 注意安全，玩的愉快！

## 法务

RoboMasterPy Playground 是一个爱好者作品，和DJI没有关系。

大疆、大疆创新、DJI、 RoboMaster是深圳市大疆创新科技有限公司的商标。

## Acknowledgement

RoboMasterPy Playground 是在机甲大师EP开发者比赛中孵化的，作者对DJI提供的硬件和技术支持表示感谢。

## 许可

RoboMasterPy 基于MIT许可发布，
您只需要保留署名和版权信息（LICENSE）即可自由使用本软件。