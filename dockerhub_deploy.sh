#! /bin/bash
cd support/docker/
docker cp $(docker ps -l -q):/build/src/target ./
find ./target -name 'redbox-distro-*-build.tar.gz' | xargs -I % cp % ./redbox.tar.gz
docker login -u $DOCKER_USER -p $DOCKER_PASS
export REPO=qcifengineering/redbox
docker pull $REPO
export TAG=`if [ "$TRAVIS_BRANCH" == "master" ]; then echo "latest"; else echo $TRAVIS_BRANCH; fi`
docker build -f Dockerfile -t $REPO:$COMMIT .
docker tag $REPO:$COMMIT $REPO:$TAG
docker tag $REPO:$COMMIT $REPO:travis-$TRAVIS_BUILD_NUMBER
docker push $REPO
