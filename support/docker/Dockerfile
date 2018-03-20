FROM centos:7
RUN yum install -y java-1.8.0-openjdk less cron diff gettext && yum clean all
ADD "http://dev.redboxresearchdata.com.au/nexus/service/local/artifact/maven/redirect?r=releases&g=com.googlecode.redbox-mint&a=redbox-distro&v=LATEST&c=build&e=tar.gz" /redbox.tar.gz
RUN tar xvfz redbox.tar.gz -C /opt/ && rm /redbox.tar.gz
COPY institutional-build /opt/redbox
RUN chmod +x /opt/redbox/server/*.sh
CMD /opt/redbox/server/tf_fg.sh
