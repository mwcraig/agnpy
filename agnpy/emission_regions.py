import numpy as np
import astropy.units as u
from astropy.constants import e, c, m_e, sigma_T
from astropy.coordinates import Distance
import matplotlib.pyplot as plt
from . import spectra


e = e.gauss
mec2 = m_e.to("erg", equivalencies=u.mass_energy())
# equivalency for decomposing Gauss in Gaussian-cgs units (not available in astropy)
Gauss_cgs_unit = "cm(-1/2) g(1/2) s-1"
Gauss_cgs_equivalency = [(u.G, u.Unit(Gauss_cgs_unit), lambda x: x, lambda x: x)]


__all__ = ["Blob"]


class Blob:
    r"""Simple spherical emission region.

    **Note:** all these quantities are defined in the comoving frame so they are actually
    primed quantities, when referring the notation in [DermerMenon2009]_.

    Parameters
    ----------
    R_b : :class:`~astropy.units.Quantity`
        radius of the blob
    z : float
        redshift of the source
    delta_D : float
        Doppler factor of the relativistic outflow
    Gamma : float
        Lorentz factor of the relativistic outflow
    B : :class:`~astropy.units.Quantity`
        magnetic field in the blob (Gauss)
    xi : float
        acceleration coefficient :math:`\xi` for first-order Fermi acceleration
        :math:`(\mathrm{d}E/\mathrm{d}t \propto v \approx c)`
        used to compute limits on the maximum Lorentz factor via
        :math:`(\mathrm{d}E/\mathrm{d}t)_{\mathrm{acc}} = \xi c E / R_L`

    spectrum_norm : :class:`~astropy.units.Quantity`
        normalisation of the electron spectra, by default can be, following 
        the notation in [DermerMenon2009]_:

            - :math:`n_{e,\,tot}`: total electrons density, in :math:`\mathrm{cm}^{-3}`
            - :math:`u_e` : total electrons energy density, in :math:`\mathrm{erg}\,\mathrm{cm}^{-3}`
            - :math:`W_e` : total energy in electrons, in :math:`\mathrm{erg}`
        
        see `spectrum_norm_type` for more details on the normalisation

    spectrum_dict : dictionary
        dictionary containing type and spectral shape information, e.g.:

        .. code-block:: python

            spectrum_dict = {
                "type": "PowerLaw", 
                "parameters": {
                    "p": 2.8, 
                    "gamma_min": 1e2, 
                    "gamma_max": 1e7
                }
            }

    spectrum_norm_type : ["integral", "differential", "gamma=1"]
        only with a normalisation in "cm-3" one can select among three types: 

        * `integral`: (default) the spectrum is set such that :math:`n_{e,\,tot}` equals the value provided by `spectrum_norm`;  
        
        * `differential`: the spectrum is set such that :math:`k_e` equals the value provided by `spectrum_norm`;    
        
        * `gamma=1`: the spectrum is set such that :math:`n_e(\gamma=1)` equals the value provided by `spectrum_norm`.
        
    gamma_size : int
        size of the array of electrons Lorentz factors
    """

    def __init__(
        self,
        R_b,
        z,
        delta_D,
        Gamma,
        B,
        spectrum_norm,
        spectrum_dict,
        spectrum_norm_type="integral",
        xi=1.0,
        gamma_size=200,
    ):
        self.R_b = R_b.to("cm")
        self.z = z
        self.d_L = Distance(z=self.z).cgs
        self.V_b = 4 / 3 * np.pi * np.power(self.R_b, 3)
        self.delta_D = delta_D
        self.Gamma = Gamma
        self.Beta = np.sqrt(1 - 1 / np.power(self.Gamma, 2))
        # viewing angle
        self.mu_s = (1 - 1 / (self.Gamma * self.delta_D)) / self.Beta
        self.theta_s = (np.arccos(self.mu_s) * u.rad).to("deg")
        self.B = B
        # B decomposed in Gaussian-cgs units
        self.B_cgs = B.to(Gauss_cgs_unit, equivalencies=Gauss_cgs_equivalency)
        self.spectrum_norm = spectrum_norm
        self.spectrum_norm_type = spectrum_norm_type
        self.spectrum_dict = spectrum_dict
        self.xi = xi
        # size of the electron Lorentz factor grid
        self.gamma_size = gamma_size
        self.gamma_min = self.spectrum_dict["parameters"]["gamma_min"]
        self.gamma_max = self.spectrum_dict["parameters"]["gamma_max"]
        # grid of Lorentz factor for the integration in the blob comoving frame
        self.gamma = np.logspace(
            np.log10(self.gamma_min), np.log10(self.gamma_max), self.gamma_size
        )
        # grid of Lorentz factors for integration in the external frame
        self.gamma_to_integrate = np.logspace(1, 9, self.gamma_size)
        # model for the electron density
        self.set_n_e(self.spectrum_norm, self.spectrum_dict, self.spectrum_norm_type)

    def set_n_e(self, spectrum_norm, spectrum_dict, spectrum_norm_type):
        r"""set the spectrum :math:`n_e` for the blob"""
        model_dict = {
            "PowerLaw": spectra.PowerLaw,
            "BrokenPowerLaw": spectra.BrokenPowerLaw,
            "BrokenPowerLaw2": spectra.BrokenPowerLaw2,
        }
        spectrum_type = spectrum_dict["type"]

        if spectrum_norm_type != "integral" and spectrum_norm.unit in (
            u.Unit("erg"),
            u.Unit("erg cm-3"),
        ):
            raise NameError(
                "Normalisations different than 'integral' available only for 'spectrum_norm' in cm-3"
            )

        # check the units of the normalisation
        # cm-3 is the only one allowing more than one normalisation type
        if spectrum_norm.unit == u.Unit("cm-3"):

            if spectrum_norm_type == "integral":
                self.n_e = model_dict[spectrum_type].from_normalised_density(
                    spectrum_norm, **spectrum_dict["parameters"]
                )
            elif spectrum_norm_type == "differential":
                self.n_e = model_dict[spectrum_type](
                    spectrum_norm, **spectrum_dict["parameters"]
                )
            elif spectrum_norm_type == "gamma=1":
                self.n_e = model_dict[spectrum_type].from_norm_at_gamma_1(
                    spectrum_norm, **spectrum_dict["parameters"]
                )

        elif spectrum_norm.unit == u.Unit("erg cm-3"):
            self.n_e = model_dict[spectrum_type].from_normalised_u_e(
                spectrum_norm, **spectrum_dict["parameters"]
            )

        elif spectrum_norm.unit == u.Unit("erg"):
            u_e = (spectrum_norm / self.V_b).to("erg cm-3")
            self.n_e = model_dict[spectrum_type].from_normalised_u_e(
                u_e, **spectrum_dict["parameters"]
            )

    def __str__(self):
        """printable summary of the blob"""
        return (
            "* spherical emission region\n"
            + f" - R_b (radius of the blob): {self.R_b.cgs:.2e}\n"
            + f" - V_b (volume of the blob): {self.V_b.cgs:.2e}\n"
            + f" - z (source redshift): {self.z:.2f}\n"
            + f" - d_L (source luminosity distance):{self.d_L.cgs:.2e}\n"
            + f" - delta_D (blob Doppler factor): {self.delta_D:.2e}\n"
            + f" - Gamma (blob Lorentz factor): {self.Gamma:.2e}\n"
            + f" - Beta (blob relativistic velocity): {self.Beta:.2e}\n"
            + f" - theta_s (jet viewing angle): {self.theta_s:.2e}\n"
            + f" - B (magnetic field tangled to the jet): {self.B:.2e}\n"
            + str(self.n_e)
        )

    def set_delta_D(self, Gamma, theta_s):
        """set the viewing angle and the Lorentz factor of the outflow to
        obtain a specific Doppler factor

        Parameters
        ----------
        Gamma : float
            Lorentz factor of the relativistic outflow
        theta_s : :class:`~astropy.units.Quantity`
            viewing angle of the jet
        """
        mu_s = np.cos(theta_s.to("rad").value)
        Beta = np.sqrt(1 - 1 / np.power(Gamma, 2))
        delta_D = 1 / (Gamma * (1 - Beta * mu_s))

        self.theta_s = theta_s
        self.mu_s = mu_s
        self.Gamma = Gamma
        self.Beta = Beta
        self.delta_D = delta_D

    def set_gamma_size(self, gamma_size):
        """change size of the array of electrons Lorentz factors"""
        self.gamma_size = gamma_size
        self.gamma = np.logspace(
            np.log10(self.gamma_min), np.log10(self.gamma_max), self.gamma_size
        )
        self.gamma_to_integrate = np.logspace(1, 9, self.gamma_size)

    def N_e(self, gamma):
        r"""number of electrons as a function of the Lorentz factor, 
        :math:`N_e(\gamma') = V_b\,n_e(\gamma')`"""
        return self.V_b * self.n_e(gamma)

    @property
    def n_e_tot(self):
        r"""total electrons density

        .. math::
            n_{e,\,tot} = \int^{\gamma'_{\rm max}}_{\gamma'_{\rm min}} {\rm d}\gamma' n_e(\gamma')
        """
        return np.trapz(self.n_e(self.gamma), self.gamma)

    @property
    def N_e_tot(self):
        r"""total number of electrons

        .. math::
            N_{e,\,tot} = \int^{\gamma'_{\rm max}}_{\gamma'_{\rm min}} {\rm d}\gamma' N_e(\gamma')
        """
        return np.trapz(self.N_e(self.gamma), self.gamma)

    @property
    def u_e(self):
        r"""total energy density in non-thermal electrons

        .. math::
            u_{e} = m_e c^2\,\int^{\gamma'_{\rm max}}_{\gamma'_{\rm min}} {\rm d}\gamma' \gamma' n_e(\gamma')
        """
        return mec2 * np.trapz(self.gamma * self.n_e(self.gamma), self.gamma)

    @property
    def W_e(self):
        r"""total energy in non-thermal electrons

        .. math::
            W_{e} = m_e c^2\,\int^{\gamma'_{\rm max}}_{\gamma'_{\rm min}} {\rm}\gamma' \gamma' N_e(\gamma')
        """
        return mec2 * np.trapz(self.gamma * self.N_e(self.gamma), self.gamma)

    @property
    def U_B(self):
        r"""energy density of magnetic field

        .. math::
            U_B = B^2 / (8 \pi)
        """
        U_B = np.power(self.B_cgs, 2) / (8 * np.pi)
        return U_B.to("erg cm-3")

    @property
    def k_eq(self):
        """equipartition parameter: ratio between totoal electron energy density  
        magnetic field energy density, Eq. 7.75 of [DermerMenon2009]_"""
        return (self.u_e / self.U_B).to_value("")

    @property
    def P_jet_e(self):
        r"""jet power in electrons

        .. math::
            P_{jet,\,e} = 2 \pi R_b^2 \beta \Gamma^2 c u_e
        """
        prefactor = (
            2 * np.pi * np.power(self.R_b, 2) * self.Beta * np.power(self.Gamma, 2) * c
        )
        return (prefactor * self.u_e).to("erg s-1")

    @property
    def P_jet_B(self):
        r"""jet power in magnetic field

        .. math::
            P_{jet,\,B} = 2 \pi R_b^2 beta \Gamma^2 c \frac{B^2}{8\pi}
        """
        prefactor = (
            2 * np.pi * np.power(self.R_b, 2) * self.Beta * np.power(self.Gamma, 2) * c
        )
        return (prefactor * self.U_B).to("erg s-1")

    @property
    def gamma_max_larmor(self):
        r"""maximum Lorentz factor of electrons that have their Larmour radius 
        smaller than the blob radius: :math:`R_L < R_b`. 
        The Larmor frequency and radius in Gaussian units read

        .. math::

            \omega_L &= \frac{eB}{\gamma m_e c} \\
            R_L &= \frac{v}{\omega_L} = \frac{\gamma m_e v c}{e B} \approx \frac{\gamma m_e c^2}{e B}

        therefore

        .. math::

            R_L < R_b \Rightarrow \gamma_{\mathrm{max}} < \frac{R_b e B}{m_e c^2}
        """
        return (self.R_b * e * self.B_cgs / mec2).to_value("")

    @property
    def gamma_max_ballistic(self):
        r"""Naive estimation of maximum Lorentz factor of electrons comparing 
        acceleration time scale with ballistic time scale. 
        For the latter we assume that the particles crosses the blob radius.

        .. math::

            (\mathrm{d}E/\mathrm{d}t)_{\mathrm{acc}} &= \xi c E / R_L \\
            T_{\mathrm{acc}} &= E \,/\,(\mathrm{d}E/\mathrm{d}t)_{\mathrm{acc}} = R_L / (\xi c) \\
            T_{\mathrm{bal}} &= R_b / c \\
            T_{\mathrm{acc}} &< T_{\mathrm{bal}} 
            \Rightarrow \gamma_{\mathrm{max}} < \frac{\xi  R_b e B}{m_e c^2} 
        """
        return self.xi * self.gamma_max_larmor

    @property
    def gamma_max_synch(self):
        r"""Simple estimation of maximum Lorentz factor of electrons 
        comparing the acceleration time scale with the synchrotron energy loss

        .. math::
            (\mathrm{d}E/\mathrm{d}t)_{\mathrm{acc}} &= \xi c E / R_L \\
            (\mathrm{d}E/\mathrm{d}t)_{\mathrm{synch}} &= 4 / 3 \sigma_T c U_B \gamma^2 \\
            (\mathrm{d}E/\mathrm{d}t)_{\mathrm{acc}} &= (\mathrm{d}E/\mathrm{d}t)_{\mathrm{synch}} 
            \Rightarrow \gamma_{\mathrm{max}} < \sqrt{\frac{6 \pi \xi e}{\sigma_T B}}
        """
        return np.sqrt(6 * np.pi * self.xi * e / (sigma_T * self.B_cgs)).to_value("")

    @property
    def gamma_max_SSC(self):
        r"""Simple estimation of maximum Lorentz factor of electrons 
        comparing the acceleration time scale with the SSC energy loss (in Thomson range)
        WARNING: the highest energy electrons will most often scatter in Klein-Nishina range instead

        .. math::
            (\mathrm{d}E/\mathrm{d}t)_{\mathrm{acc}} &= \xi c E / R_L \\
            (\mathrm{d}E/\mathrm{d}t)_{\mathrm{SSC}} &= 4 / 3 \sigma_T c U_{\mathrm{synch}} \gamma^2 \\
            (\mathrm{d}E/\mathrm{d}t)_{\mathrm{acc}} &= (\mathrm{d}E/\mathrm{d}t)_{\mathrm{SSC}} 
            \Rightarrow \gamma_{\mathrm{max}} < \sqrt{\frac{3 \xi e B }{\sigma_T U_SSC}}
        """
        return np.sqrt(
            3 * self.xi * e * self.B_cgs / (4 * sigma_T * self.u_ph_synch)
        ).to_value("")

    def gamma_max_EC_DT(self, dt, r=0 * u.cm):
        r"""Simple estimation of maximum Lorentz factor of electrons comparing the acceleration time scale 
        with the EC energy loss (in Thomson range, see B&G 1970), like in gamma_max_SSC 
        WARNING: assumes Thomson regime

        .. math::            
            \gamma_{\mathrm{max}} = \sqrt{\frac{3 \xi e B }{ \sigma_T U'_\mathrm{ext}}} 
        """
        return np.sqrt(
            3 * self.xi * e * self.B_cgs / (4 * sigma_T * dt.u_ph(r, self))
        ).to_value("")

    @property
    def gamma_break_synch(self):
        r"""Simple estimation of the cooling break of electrons comparing 
        synchrotron cooling time scale with the ballistic time scale: 
        
        .. math::

            T_{\mathrm{synch}} &= E\,/\,(\mathrm{d}E/\mathrm{d}t)_{\mathrm{synch}} 
            =  3 m_e c^2 / (4 \sigma_T U_B \gamma) \\
            T_{\mathrm{bal}} &= R_b / c \\
            T_{\mathrm{synch}} &= T_{\mathrm{bal}} \Rightarrow \gamma_b = 6 \pi m_e c^2 / \sigma_T B^2 R_b 
        """
        gamma_max = (
            (6 * np.pi * mec2 / (sigma_T * np.power(self.B_cgs, 2) * self.R_b))
            .to("")
            .value
        )
        return gamma_max

    @property
    def gamma_break_SSC(self):
        r"""Simple estimation of the cooling break of electrons comparing 
        SSC time scale (see B&G 1970) with the ballistic time scale: 
        WARNING: only applicable in Thomson regime

        .. math::
            T_{\mathrm{SSC}} &= E\,/\,(\mathrm{d}E/\mathrm{d}t)_{\mathrm{SSC}} 
            =  3 m_e c^2 / (4 \sigma_T U_{\mathrm{SSC}} \gamma) \\
            T_{\mathrm{bal}} &= R_b / c \\
            T_{\mathrm{SSC}} &= T_{\mathrm{bal}} \Rightarrow \gamma_b = 3  m_e c^2 / 4 \sigma_T U_{\mathrm{SSC}} R_b 
        """
        return (3 * mec2 / (4 * sigma_T * self.u_ph_synch * self.R_b)).to("").value

    def gamma_break_EC_DT(self, dt, r=0 * u.cm):
        r"""Simple estimation of the cooling break of electrons comparing 
        EC time scale (see B&G 1970) with the ballistic time scale, like in gamma_break_SSC 
        WARNING: assumes Thomson regime

        .. math::            
            \gamma_b = 3  m_e c^2 / 4 \sigma_T U'_{\mathrm{ext}} R_b 
        """
        #        u_ext=np.power(self.Gamma,2) * np.power(1-mu*self.Beta,2) * dt.xi_dt*dt.L_disk/(4*np.pi*np.power(d,2) * c)
        return (3 * mec2 / (4 * sigma_T * dt.u_ph(r, self) * self.R_b)).to("").value

    @property
    def u_ph_synch(self):
        r"""energy density of the synchrotron photons energy losses are:

        .. math::        
            (\mathrm{d}E/\mathrm{d}t)_{\mathrm{synch}} = 4 / 3 \sigma_T c U_B \gamma^2 

        the radiation stays an average time of :math:`(3/4) (R_b/c)` (the factor of 3/4 cames from averaging over a sphere), 
        so an e- with Lorentz factor :math:`\gamma` produces:

        .. math::        
            0.75\,(\mathrm{d}E/\mathrm{d}t)_{\mathrm{synch}}\,(R_b/c)\,/\,V_b 

        of radiation. We need to integrate over the electron spectrum  (and multiply back by V_b)

        .. math::        
            0.75\,\int n_e(\gamma) (\mathrm{d}E/\mathrm{d}t)_{\mathrm{synch}}  R_b  \mathrm{d}\gamma
        
        so

        .. math::        
            u_{\mathrm{synch}} = \sigma_T  U_B  R_b  \int n_e(\gamma) \, \gamma^2 \mathrm{d}\gamma

        WARNING: this does not take into account SSA!
        """
        u_ph = (
            sigma_T.cgs
            * self.U_B
            * self.R_b
            * np.trapz(np.power(self.gamma, 2) * self.n_e(self.gamma), self.gamma)
        )
        return u_ph.to("erg cm-3")

    def plot_n_e(self, ax=None, gamma_power=0):
        """plot the  electron distribution
        
        Parameters 
        ----------
        ax : :class:`~matplotlib.axes.Axes`, optional
            Axis
        gamma_power : float
            power of gamma to raise the electron distribution
        """
        ax = plt.gca() if ax is None else ax

        ax.loglog(self.gamma, np.power(self.gamma, gamma_power) * self.n_e(self.gamma))
        ax.set_xlabel(r"$\gamma$")
        if gamma_power == 0:
            ax.set_ylabel(r"$n_e(\gamma)\,/\,{\rm cm}^{-3}$")
        else:
            ax.set_ylabel(
                r"$\gamma^{"
                + str(gamma_power)
                + r"}$"
                + r"$\,n_e(\gamma)\,/\,{\rm cm}^{-3}$"
            )
        return ax
