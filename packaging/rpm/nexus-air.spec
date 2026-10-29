Name:           nexus-air
Version:        1.0.0
Release:        1%{?dist}
Summary:        Linux driver and GTK4 GUI for Claw's Nexus Air V1 gaming mouse

License:        MIT
URL:            https://github.com/morluto/nexus-air-linux
Source0:        %{name}-%{version}.tar.gz
BuildArch:      noarch

BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
BuildRequires:  python3-pip
BuildRequires:  python3-wheel

Requires:       python3 >= 3.10
Requires:       python3-gobject
Requires:       gtk4

%description
Nexus Air Linux is a reverse-engineered Linux driver, command line tool,
and modern GTK4 configuration GUI for Claw's Nexus Air V1 wireless and wired
gaming mouse.

%prep
%autosetup

%build
%py3_build

%install
%py3_install
install -Dm644 data/org.cachyos.NexusAirV1.desktop %{buildroot}%{_datadir}/applications/org.cachyos.NexusAirV1.desktop
install -Dm644 data/icons/nexus-air.svg %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/nexus-air.svg
install -Dm644 data/99-nexus-air.rules %{buildroot}%{_udevrulesdir}/99-nexus-air.rules

%files
%license LICENSE
%{_bindir}/nexus-air
%{_bindir}/nexus-air-gui
%{python3_sitelib}/nexus_air/
%{python3_sitelib}/nexus_air-*.egg-info/
%{_datadir}/applications/org.cachyos.NexusAirV1.desktop
%{_datadir}/icons/hicolor/scalable/apps/nexus-air.svg
%{_udevrulesdir}/99-nexus-air.rules

%changelog
* Wed Oct 29 2026 Nexus Air Contributors <info@example.com> - 1.0.0-1
- Initial release for Claw's Nexus Air V1.
