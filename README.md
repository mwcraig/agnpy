# agnpy
<p align="center">
  <img width="60%" src="docs/_static/logo.png">
</p>

Modelling Active Galactic Nuclei radiative processes with python.

## descritpion
`agnpy` focuses on the numerical computation of the photon spectra produced by leptonic radiative processes in jetted Active Galactic Nuclei (AGN).  

## documentation and quickstart
You are invited to check the documentation at https://agnpy.readthedocs.io/en/latest/.    
To get familiar with the code you can run the notebooks in the `tutorials` section
of the documentation.

## dependencies
The only dependencies are:

* [numpy](https://numpy.org) managing the numerical computation;

* [astropy](https://www.astropy.org) managing physical units and astronomical distances.

* [matplotlib](https://matplotlib.org) for visualisation and reproduction of the tutorials.

## installation
The code is available in the [python package index](https://pypi.org/project/agnpy/) and can be installed via `pip`

```bash
pip install agnpy
```

## tests
A test suite is available in [`agnpy/tests`](https://github.com/cosimoNigro/agnpy/tree/master/agnpy/tests), to run it just type
`pytest` in the main directory.

## shields
![](https://github.com/cosimoNigro/agnpy/workflows/CI%20test/badge.svg)

![](https://codecov.io/gh/cosimoNigro/agnpy/branch/master/graph/badge.svg)

![](http://img.shields.io/pypi/v/agnpy.svg?text=version)
