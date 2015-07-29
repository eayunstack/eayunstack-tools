Name:		eayunstack-tools
Version:	1.0
Release:	19%{?dist}
Summary:	EayunStack Management tools

Group:		Application
License:	GPL
URL:		https://github.com/eayunstack/eayunstack-tools
Source0:	eayunstack-tools-%{version}.tar.gz

BuildRequires:	/bin/bash
BuildRequires:	python
BuildRequires:	python2-devel
BuildRequires:	python-setuptools
Requires:	python
Requires:	MySQL-python
Requires:	python-paramiko
Requires:	python-fuelclient
Requires:	python-cinder
Requires:	kernel-tools
Requires:	ipmitool

%description
EayunStack Management Tools

%prep
%setup -q


%build
CFLAGS="$RPM_OPT_FLAGS" %{__python2} setup.py build


%install
rm -rf %{buildroot}
%{__python2} setup.py install --skip-build --root %{buildroot}
mkdir -p %{buildroot}/.eayunstack/
cp -r template %{buildroot}/.eayunstack/

%post
if [ "$1" = "1" ]; then

useradd eayunadm &> /dev/null
passwd -d eayunadm &> /dev/null
passwd -e eayunadm &> /dev/null
echo 'eayunadm	ALL=(ALL)	NOPASSWD:/bin/eayunstack' >> /etc/sudoers

echo 'Defaults !requiretty' > /etc/sudoers.d/eayunstack-tools

# modify PS1
echo '
# write by eayunstack-tools
if [ -f /.eayunstack/node-role ];then
    noderole=`cat /.eayunstack/node-role`
    export PS1="[\u@\h \W]($noderole)\\$ "
fi

' >> /etc/bashrc
fi

%postun
if [ "$1" = "0" ]; then
    sed -i -e '/^eayunadm/d' /etc/sudoers
    rm -rf /etc/sudoers.d/eayunstack-tools
fi


%files
%doc
%attr(0755,root,root)/.eayunstack
/usr/bin/eayunstack
/usr/lib/python2.7/site-packages/


%changelog
* Wed Jul 29 2015 blkart <blkart.org@gmail.com> 1.0-19
- commit 9827cf716906cc822d59c8bd80c6d587f828bf12

* Mon Jul 27 2015 blkart <blkart.org@gmail.com> 1.0-18
- commit b25504c0a6c4f9d17c7cc33c661b362e72c7094a 

* Tue Jul 14 2015 blkart <blkart.org@gmail.com> 1.0-17
- commit 167cc599e0623c30b6f3e26cdeb6b5769f17cb81

* Mon Jun 29 2015 blkart <blkart.org@gmail.com> 1.0-16
- commit 95e40b7e6fed9e87267ad762aed90345daa77ea5

* Wed Jun 17 2015 blkart <blkart.org@gmail.com> 1.0-15
- commit bf930b3da85e573e26d03b8ee7ca7c849e710afb

* Wed Jun 17 2015 blkart <blkart.org@gmail.com> 1.0-14
- commit af9597aca212c244df067f87d746251e6d0dee77

* Mon Jun 8 2015 blkart <blkart.org@gmail.com> 1.0-13
- commit f9366b560454998cf3c4b121dc31e614787f7873

* Fri Jun 5 2015 blkart <blkart.org@gmail.com> 1.0-12
- commit 394f2aed2f27f20d65f28b83f37956cbe24cad9c

* Thu Jun 4 2015 blkart <blkart.org@gmail.com> 1.0-11
- commit 96099afaf10dac415964a3b56dd3f5664fa5bf01 

* Wed Jun 3  2015 blkart <blkart.org@gmail.com> 1.0-10
- commit 7a94fefbd9988e647e6648a442fcde32c2f46f64

* Wed Jun 3  2015 blkart <blkart.org@gmail.com> 1.0-9
- commit 5ae1356f9b7f0e8eb68b30b63abb86e85bbb8200

* Tue Jun 2  2015 blkart <blkart.org@gmail.com> 1.0-8
- commit 2533dbf3103cfd11cf6403597c3b032554e6b629

* Fri May 29 2015 blkart <blkart.org@gmail.com> 1.0-7
- commit 660939f46e795cb690152ff3d2b1a89ba990ad5c

* Thu May 21 2015 blkart <blkart.org@gmail.com> 1.0-6
- commit da268695f96db9a3f2e4edfe3ea1fa6d92fa3594

* Thu May 21 2015 blkart <blkart.org@gmail.com> 1.0-5
- commit 3a0d6325bbc310742873da20bf5c14b8ff6942f9

* Wed May 20 2015 blkart <blkart.org@gmail.com> 1.0-4
- commit 177acade7ace97f1354e5a170acbe32ec5ba3477

* Fri May 15 2015 blkart <blkart.org@gmail.com> 1.0-3
- modify spec file

* Mon May 11 2015 blkart <blkart.org@gmail.com> 1.0-2
- commit 8d9af51a016922967814707b540c7523a518ddcd
- modify spec & makefile file

* Thu May 7 2015 blkart <blkart.org@gmail.com> 1.0-1
- commit ed7658fbe90d3165591a02f06bdf9af63091c907
