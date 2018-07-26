#
# Makefile
# zuo, 2018-07-25 11:31
#

HAECEMU = haecemu/*.py
PYSRC = $(HAECEMU)
PYCFILE = $(shell find ./ -name '*.pyc')
TMP_FILE = $(PYCFILE) build dist *.egg-info

all:
	@echo "Makefile needs your attention"

errcheck: $(PYSRC)
	@echo "Running check for errors only"
	pyflakes $(PYSRC)
	pylint -E --rcfile=.pylint $(PYSRC)

cleanup:
	@echo "Cleanup tempory files"
	rm -rf $(TMP_FILE)


# vim:ft=make
#
