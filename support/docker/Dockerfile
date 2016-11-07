
FROM centos:7
RUN yum install -y wget java-1.8.0-openjdk tar
RUN wget -O redbox.tar.gz "http://dev.redboxresearchdata.com.au/nexus/service/local/artifact/maven/redirect?r=releases&g=com.googlecode.redbox-mint&a=redbox-distro&v=1.8&c=build&e=tar.gz";tar xvfz redbox.tar.gz -C /opt/;rm redbox.tar.gz;wget -O /opt/redbox/server/tf_fg.sh "https://raw.githubusercontent.com/redbox-mint/redbox/rifcs161/config/src/main/config/server/tf_fg.sh"; chmod +x /opt/redbox/server/tf_fg.sh
CMD /opt/redbox/server/tf_fg.sh