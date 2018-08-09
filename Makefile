#
# Makefile
# zuo, 2018-07-25 11:31
#

HAECEMU = haecemu/*.py
TEST = haecemu/test/*.py
EXAMPLES = ./examples/*.py
SH_SCRIPTS = ./script/*.sh
PYTHON ?= python

PYSRC = $(HAECEMU)
PYCFILE = $(shell find ./ -name '*.pyc')
TMP_FILE = $(PYCFILE) build dist *.egg-info

all:
	@echo "Makefile needs your attention"

errcheck: $(PYSRC)
	@echo "# Running check for errors only"
	pyflakes $(PYSRC)

errcheck-lint: $(PYSRC)
	@echo "# Running check for errors only"
	pyflakes $(PYSRC)
	pylint -E --rcfile=.pylint $(PYSRC)

install:
	$(PYTHON) setup.py install

develop:
	$(PYTHON) setup.py develop

cleanup:
	@echo "# Cleanup tempory files"
	rm -rf $(TMP_FILE)


# vim:ft=make
#
