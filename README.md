<p align="center">
  <h1 align="center">KTC - Klipper Toolchanger Code <sub>v.2</sub></h1>
</p>

<p align="center">
Universal Toolchanger helper for Klipper
</p>

<p align="center">
  <a aria-label="Downloads" href="https://github.com/Malaquitte/KTC/releases">
    <img src="https://img.shields.io/github/release/Malaquitte/KTC?display_name=tag&style=flat-square"  alt="Downloads Badge">
  </a>
  <a aria-label="Stars" href="https://github.com/Malaquitte/KTC/stargazers">
    <img src="https://img.shields.io/github/stars/Malaquitte/KTC?style=flat-square"  alt="Stars Badge">
  </a>
  <a aria-label="Forks" href="https://github.com/Malaquitte/KTC/network/members">
    <img src="https://img.shields.io/github/forks/Malaquitte/KTC?style=flat-square" alt="Forks Badge">
  </a>
  <a aria-label="License" href="https://github.com/Malaquitte/KTC/blob/master/LICENSE">
    <img src="https://img.shields.io/github/license/Malaquitte/KTC?style=flat-square" alt="License Badge">
  </a>
  <a aria-label="Codacy Badge" href="https://app.codacy.com/gh/Malaquitte/KTC/dashboard?utm_source=gh&utm_medium=referral&utm_content=&utm_campaign=Badge_grade">
    <img src="https://app.codacy.com/project/badge/Grade/2ba035ce6a444b889d3e9afcd5e9ec87" alt="Codacy Badge">
  </a>
</p>

This is a fork of [KTC V2](https://github.com/TypQxQ/KTC). This version takes into account multiple endstop states to determine the proper functioning of the toolchanger.

## ![#f98b00](/doc/f98b00.png) ![#fe3263](/doc/fe3263.png) ![#0fefa9](/doc/0fefa9.png) ![#085afe](/doc/085afe.png) Installation

The code requires Klipper to run on Python v.3 only.

### 1\. Automatic install with Moonraker autoupdate support
Connect to your klipper machine using SSH and run this one line command:
```
cd ~/ && git clone https://github.com/Malaquitte/KTC.git && bash ~/KTC/install.sh
```

Configure away inside printer.cfg or a file referenced by it.

### 2\. Manual Install
Copy or link the python (`*.py`) files into the `\klipper\klippy\extras` directory.

Copy the macros inside the macros folder and reference them in printer.cfg.

```
[include ktc/config/toolchanger.cfg]
[include ktc/macros/tool_macros.cfg]
```
