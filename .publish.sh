#!/usr/bin/env bash
# Deploys a Python library or application

echo "Deploying version $TRAVIS_TAG..."
# check that the version in the tag and in setup.cfg match
sed 's/ //g' setup.cfg | grep "^version=$TRAVIS_TAG" || { \
   echo "Version in tag ($TRAVIS_TAG) does not match version in setup.cfg \
($(sed 's/ //g' setup.cfg | grep '^version=' | awk -F '=' '{print $2}'))"; \
   exit 255; }

# build
python setup.py clean sdist bdist_wheel || { echo "Errors building"; exit 255; }
#upload to pypi
#generate the .pypirc file first
echo "[testpypi]" > .pypirc
#echo "[pypi]" > .pypirc
chmod 600 .pypirc
echo "username = adriand" >> .pypirc
echo "password = ${PYPI_PASSWORD}" >> .pypirc

echo "Publish on pypi ${TRAVIS_TAG}"
twine upload --config-file .pypirc dist/* || { echo "Errors publishing $TRAVIS_TAG"; exit 255; }

# check version available
pip uninstall -y pyvo
pip install --upgrade --pre pyvo==$TRAVIS_TAG || { echo "$TRAVIS_TAG not installed on pypi" ; exit 255; }
