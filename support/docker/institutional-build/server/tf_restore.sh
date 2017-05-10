#!/bin/bash
#
# get absolute path of where the script is run from
export PROG_DIR=`cd \`dirname $0\`; pwd`

# setup environment
. $PROG_DIR/tf_env.sh

# display program header
echo "Redbox - ReIndex Client - ${REDBOX_VERSION}"

echo " * Starting redbox reindexer"
LOG_FILE=$TF_HOME/logs/reindex.out
java $JAVA_OPTS -cp $CLASSPATH com.googlecode.fascinator.ReIndexClient > $LOG_FILE 2>&1
echo "   - Finished on `date`"
echo "   - Log file: $LOG_FILE"