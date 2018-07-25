#
# Makefile
# zuo, 2018-07-25 11:31
#

HAECEMU = haecemu/*.py

PYSRC = $(HAECEMU)

all:
	@echo "Makefile needs your attention"

errcheck: $(PYSRC)
	-echo "Running check for errors only"
	pyflakes $(PYSRC)
	pylint -E --rcfile=.pylint $(PYSRC)


# vim:ft=make
#
