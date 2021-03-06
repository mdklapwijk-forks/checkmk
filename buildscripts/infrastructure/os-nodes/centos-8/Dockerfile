FROM centos:centos8

SHELL ["/bin/bash", "-c"]

ARG PACKAGES

RUN yum -y --enablerepo=PowerTools --allowerasing install \
    epel-release \
    && yum -y --enablerepo=PowerTools --allowerasing install \
    curl \
    enchant \
    gcc \
    gcc-c++ \
    git \
    krb5-devel \
    make \
    mariadb \
    mysql-devel \
    nodejs \
    npm \
    openldap-devel \
    postfix \
    python2-devel \
    python27 \
    rrdtool-devel \
    strace \
    sudo \
    vim \
    which \
    && yum clean all

# RH8 does not install a python binary by default. Some of our scripts need a default python binary
# without a version suffix. The assumption is that this points to Python 2.
RUN alternatives --set python /usr/bin/python2 && python -V

# Now bring pip and pipenv to our standard version used in all environments.
RUN curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py \
    && python get-pip.py
RUN pip install --upgrade setuptools virtualenv \
    && pip install git+https://github.com/pypa/pipenv.git@2549656dc09e132d8ba2fa6327c939f5f9a951b7

RUN yum -y --enablerepo=PowerTools install \
    $PACKAGES \
    && yum clean all

# The /etc/fstab does not exist in the base image we use. A missing fstab prevents OMD from
# using a tmpfs for /omd/sites/[site]/tmp, which we want to have during our tests. We can
# simply solve this by pre-creating the empty file here.
RUN touch /etc/fstab

# New packages that are not needed for the build toolchain above should be added here.
# We avoid rebuild of the whole previous steps this way
RUN yum -y makecache \
    && yum -y --enablerepo=PowerTools install \
    joe \
    vim \
    && yum clean all

ARG VERS_TAG
RUN echo $VERS_TAG > /version.txt
