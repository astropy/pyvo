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

echo "Publish on pypi ${TRAVIS_TAG}"
export TWINE_USERNAME=adriand
export TWINE_PASSWORD=changeme112233now
export TWINE_REPOSITORY_URL=https://test.pypi.org/legacy/  #TODO comment out unless testing
twine upload --verbose dist/* || { echo "Errors publishing $TRAVIS_TAG"; exit 255; }


# check version available
pip uninstall -y pyvo
pip install --upgrade --pre pyvo==$TRAVIS_TAG || { echo "$TRAVIS_TAG not installed on pypi" ; exit 255; }
