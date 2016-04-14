Name:		eayunstack-tools
Version:	1.1
Release:	7%{?dist}
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
Requires:	python-novaclient
Requires:	python-cinderclient
Requires:	python-neutronclient
Requires:	ssmtp

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
%attr(0750,root,root)/.eayunstack
/usr/bin/eayunstack
/usr/lib/python2.7/site-packages/


%changelog
* Tue Apr 12 2016 pq     <19921207pq@gmail.com> 1.1-7
- commit d9766cca407cdac3f0e64a7d6e9de8ee24a3418f

* Mon Mar 14 2016 blkart <blkart.org@gmail.com> 1.1-6
- commit 64dedfff02fa015a2295326c7483060714a7b1b4

* Fri Feb 26 2016 blkart <blkart.org@gmail.com> 1.1-5
- commit 68841260b69ef56b46ca666b92317b6806c6b4ab

* Thu Jan 28 2016 blkart <blkart.org@gmail.com> 1.1-4
- commit e32e5bcf75185e4dd645078530ecee9c8b125c75

* Wed Jan 5 2016 blkart <blkart.org@gmail.com> 1.1-3
- commit b58194e07513766c0df3d956ac097e2731d31b04

* Tue Jan 5 2016 blkart <blkart.org@gmail.com> 1.1-2
- commit a6209478516a6a37f278d9e442daa734e9c92c57

* Tue Jan 5 2016 blkart <blkart.org@gmail.com> 1.1-1
- commit 2c63d340a5dd81faf053b3202f804518e1cb159d

* Tue Nov 3 2015 blkart <blkart.org@gmail.com> 1.0-29
- commit 3fe5e3685a0b726f848fe66f73763416e5357155

* Tue Oct 13 2015 blkart <blkart.org@gmail.com> 1.0-28
- commit a705cc9b6359f0ba6c138ae8479704092f82545f

* Fri Sep 25 2015 blkart <blkart.org@gmail.com> 1.0-27
- commit dcd6067580efec3a8b7515167693eac169900bd6

* Fri Sep 25 2015 blkart <blkart.org@gmail.com> 1.0-26
- commit be804da53d5991c4b5c9c81266cd7bc14c100b9b

* Sun Sep 20 2015 blkart <blkart.org@gmail.com> 1.0-25
- commit 860dde0db67c811139a369dc5a3f12241ce5216f

* Sat Sep 19 2015 blkart <blkart.org@gmail.com> 1.0-24
- commit 5a2eccb3ea99654ace34ef8c17c1b592a41968d7

* Thu Aug 20 2015 blkart <blkart.org@gmail.com> 1.0-23
- commit df8e3433170ca97bfc534d1c4942a3adfb7209e6

* Tue Aug 18 2015 blkart <blkart.org@gmail.com> 1.0-22
- commit c1fa414a4a76f93ee408b8ddc25c2615693958c2

* Tue Aug 4 2015 blkart <blkart.org@gmail.com> 1.0-21
- commit fb21b14762ae9e51b0ea727ad1a0a12dc877122b

* Wed Jul 29 2015 blkart <blkart.org@gmail.com> 1.0-20
- commit 95fdfa13a09e7a5a3154d1cb89f3dba9caf5804c

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
