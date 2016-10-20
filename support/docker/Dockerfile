FROM centos:7
RUN yum install -y wget java-1.8.0-openjdk tar
RUN wget -O redbox.tar.gz "http://dev.redboxresearchdata.com.au/nexus/service/local/artifact/maven/redirect?r=snapshots&g=com.googlecode.redbox-mint&a=redbox-distro&v=LATEST&c=build&e=tar.gz"
RUN tar xvfz redbox.tar.gz -C /opt/
RUN rm /redbox.tar.gz
RUN chmod +x /opt/redbox/server/tf_fg.sh
CMD /opt/redbox/server/tf_fg.sh