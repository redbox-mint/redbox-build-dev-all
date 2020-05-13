#!/bin/bash
#
# this script controls the fascinator using jetty
#
# get absolute path of where the script is run from
export PROG_DIR=`cd \`dirname $0\`; pwd`

# file to store pid
PID_FILE=$PROG_DIR/tf.pid

# display program header
echo "The Fascinator - ReDBox - $REDBOX_VERSION"

usage() {
	echo "Usage: `basename $0` {start|stop|restart|status}"
	exit 1
}

# check script arguments
# [ $# -gt 0 ] || usage

if [ ! -d "/opt/redbox/data/solr" ]; then
# the solr directory doesn't exist probably due to /opt/redbox/data being mounted to host first time
# download empty solr directory and place it in the correct location so the application can start correctly
  curl -L -o solr.tgz "http://dev.redboxresearchdata.com.au/nexus/service/local/artifact/maven/redirect?r=releases&g=au.com.redboxresearchdata&a=redbox-solr-index&v=LATEST&e=tar.gz"
  tar xvfz solr.tgz -C /opt/redbox/data
  rm -f solr.tgz
fi


# configure environment
envsubst < /opt/redbox/apikeys.json.template > /opt/redbox/data/security/apiKeys.json
. $PROG_DIR/tf_env.sh

# perform action
shift
ARGS="$*"
exitval=0
start() {
	echo " * Starting The Fascinator..."
	echo "   - Log files in $TF_HOME/logs"

	mkdir -p $TF_HOME/logs
        cd $PROG_DIR/jetty
        java $JAVA_OPTS -DSTART=start.config -jar start.jar
        cd - &> /dev/null
	exitval=0
}



# case "$ACTION" in
# start)
start
exit $exitval
