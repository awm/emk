emk
===

Build system, written in Python. Requires Python 2.6 or higher; Python 3+ is supported.

Currently supports OS X and Linux. Windows support is planned.

Features
--------

 * Fast builds. emk is designed to use multiple threads, and uses as many threads as you have processors
   by default. Build time scales linearly with the number of executed build rules.
 * Designed for correct recursive builds (ie, building in multiple directories that are dependent on
   each other). Note that emk only uses a single process for recursive builds; it does not spawn a new
   process for each directory. This allows a global view of the build graph so that correctness is easy.
 * Allows configuration of the build at the global, project, or directory level.
 * Build rules are written in Python, so anything that Python can do can be done while building. It is
   easy to write new build rules.
 * Allows specification of build rules that produce multiple files (eg code generation), as well as rules
   that do not produce any files.
 * Includes a module system for common build rules. Comes with modules for building C, C++, and Java.
 * Fancy output formatting system - can output plain text, colored/styled console output (using ANSI escape codes),
   or HTML (suitable for CSS styling).
 * Cache system for storing information between builds.
 * Allows new build rules to be added after building has started. This allows (for example) autodetection
   of executables based on the compiled object file (by parsing the nm output) rather than trying to parse
   source code.

Installation
------------

If desired, you can run `(sudo) setup.py install` to create a symlink at /usr/bin/emk pointing to
the emk script in the current directory. You can run `(sudo) setup.py uninstall` to remove /usr/bin/emk
if it is a symlink to the emk script in the current directory.

Note that emk does not require installation; it can be run directly from any directory. The only requirement
is that the emk script and the emk.py module must be in the same directory. Typically that directory
would also contain a 'modules' directory containing the various emk modules, and optionally a 'config'
directory containing the global configuration (emk_global.py) for the emk instance.

Documentation
-------------

Run `emk -h` for basic usage information.

 * [Tutorial](docs/tutorial.md)
 * [Manual](docs/manual.md)
 * [Utility Module](docs/modules/utils.md)
 * [C/C++ Module](docs/modules/c.md)
 * [Link Module](docs/modules/link.md)
 * [Java Module](docs/modules/java.md)

There are also docstrings with detailed documentation for all public API functions/properties in the emk source code.
