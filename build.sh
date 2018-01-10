nosetests --with-doctest --with-coverage --cover-package=. --cover-erase --cover-html
pylint --reports=n --output-format=parseable --disable=C0111,C0103 *.py
