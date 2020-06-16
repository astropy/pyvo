#!/usr/bin/env bash
# Deploys a Python library or application

echo "Deploying version $TRAVIS_TAG..."
# check that the version in the tag and in setup.cfg match
sed 's/ //g' setup.cfg | grep "^version=$version" || { \
   echo "Version in tag ($TRAVIS_TAG) does not match version in setup.cfg \
($(sed 's/ //g' setup.cfg | grep '^version=' | awk -F '=' '{print $2}'))"; \
   exit -1; }

# build
python setup.py clean sdist || { echo "Errors building"; exit -1; }
# upload to pypi
# generate the .pypirc file first
#echo "[pypi]" > .pypirc
#chmod 600 .pypirc
#echo "username = Canadian.Astronomy.Data.Centre" >> .pypirc
#echo "password = ${PYPI_PASSWORD}" >> .pypirc
echo "password = ${PYPI_PASSWORD}"

echo "Publish on pypi ${TRAVIS_TAG}"
#twine upload --config-file .pypirc dist/* || { echo "Errors publishing $TRAVIS_TAG"; exit -1; }

# check version available
#pip uninstall -y $product
#pip install --upgrade --pre $product==$version || { echo "$TRAVIS_TAG not installed on pypi" ; exit -1; } 
