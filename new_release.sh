#!/usr/bin/env bash

rm -rf dist/
python3 setup.py bdist_wheel

python3 -m pip install --user --upgrade twine
python3 -m twine upload dist/*
