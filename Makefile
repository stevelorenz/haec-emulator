#
# Makefile
# zuo, 2018-07-25 11:31
#

HAECEMU = haecemu/*.py
CONTROLLER_APPS = controller/*.py
TEST = $(shell find haecemu/test -name '*.py')
EXAMPLES = ./examples/*.py
SH_SCRIPTS = ./script/*.sh
PYTHON ?= python

PYSRC = $(HAECEMU) $(CONTROLLER_APPS)
PYCFILE = $(shell find ./ -name '*.pyc')
TMP_FILE = $(PYCFILE) build dist *.egg-info

all:
	@echo "Makefile needs your attention"

errcheck: $(PYSRC)
	@echo "# Running check for errors only"
	pyflakes $(PYSRC)

errcheck-all: $(PYSRC) $(TEST)
	@echo "# Running check for errors only"
	pyflakes $(PYSRC) $(TEST)

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

pip-freeze:
	@echo "# Freeze pip packages"
	pip freeze > ./dev_requirements.txt

pip-uninstall-all:
	@echo "# Uninstall all pip packages"
	pip freeze | xargs pip uninstall -y

# vim:ft=make
#
