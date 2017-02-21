Movescount-sync
===============

A CLI tool for batch-exporting GPS tracks from movescount.com.

Supported formats:

* GPX
* KML
* FIT
* TCX
* XLSX

Installation
------------

::

    pip install movescount-sync

Usage
-----

::

    movescount-sync

Configuration is created during first run and persisted in
``~/.config/movescount-sync``.

Arguments:

* ``--configure`` forces configuration wizard.
* ``--recursive`` fetches entire event stream from movescount.com instead of
  just the most recent events.
* ``--debug`` shows HTTP debugging logs.
