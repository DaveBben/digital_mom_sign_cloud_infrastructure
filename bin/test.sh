set -e

if [ -z "$@" ]
then
    coverage run -m unittest discover -s ./test -v
else
    coverage run -m unittest "$@" -v
fi
coverage report -m --include="backend/*.py"
# coverage html
