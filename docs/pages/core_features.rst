..  SPDX-FileCopyrightText: 2024 Ivan Perevala <ivan95perevala@gmail.com>

..  SPDX-License-Identifier: GPL-3.0-or-later

Features
========

Package offers a few advantages for logging:

* **Blender addon integration** - its easy to inject into existing addons. ``bhqprprt`` uses function decorators for registration functions and operator execution methods and provides functions for UI display, structure members logging, etc.

* **Colored console output** - logs should be human-readable. Its easier to find red message in the console than "WARNING" word. ``bhqrprt`` uses ASCII escape sequences to achieve this.

* **Output both into file and console** - console logs should contain only logging messages which might be important for user, while file logs should contain all possible information for debugging.
