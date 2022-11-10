"""
This Veros setup file was generated by

   $ veros copy-setup global_4deg

on 2022-05-26 12:42:55 UTC.
"""

__VEROS_VERSION__ = '1.4.3'

if __name__ == "__main__":
    raise RuntimeError(
        "Veros setups cannot be executed directly. "
        f"Try `veros run {__file__}` instead."
    )

# -- end of auto-generated header, original file below --

import os
import h5netcdf
import netCDF4

import veros.tools
from veros import VerosSetup, veros_routine, veros_kernel, KernelOutput, logger
from veros.variables import Variable
from veros.core.operators import numpy as npx, update, at

BASE_PATH = os.path.dirname(os.path.realpath(__file__))
DATA_FILES = veros.tools.get_assets("global_4deg", os.path.join(BASE_PATH, "assets.json"))

PATH = '/Users/jgaertne/Documents/forcing data/'
DATA_ML = 'era5_198x_ml_4x4deg_monthly_mean.nc'
DATA_SFC = 'era5_198x_sfc_4x4deg_monthly_mean.nc'


import versis
from versis.flux_atmOcn_atmIce import main as heat_flux


class GlobalFourDegreeSetup(VerosSetup):

    __veros_plugins__ = (versis,)

    """Global 4 degree model with 15 vertical levels.

    This setup demonstrates:
     - setting up a realistic model
     - reading input data from external files
     - including Indonesian throughflow
     - implementing surface forcings
     - implementing an ice model

    `Adapted from pyOM2 <https://wiki.cen.uni-hamburg.de/ifm/TO/pyOM2/4x4%20global%20model>`_.

    ChangeLog
     - 07-05-2020: modify bathymetry in order to include Indonesian throughflow;
       courtesy of Franka Jesse, Utrecht University

    """

    min_depth = 10.0
    max_depth = 5400.0

    fine_z = False # flag for using a finer vertical resolution

    @veros_routine
    def set_parameter(self, state):
        settings = state.settings

        settings.identifier = "4deg"

        settings.nx, settings.ny = 90, 40
        if self.fine_z:
            settings.nz = 40
        else:
            settings.nz = 15
        settings.dt_mom = 1800.0
        settings.dt_tracer = 86400.0
        settings.runlen = 86400 * 180

        settings.x_origin = 4.0
        settings.y_origin = -76.0

        settings.coord_degree = True
        settings.enable_cyclic_x = True

        settings.enable_neutral_diffusion = True
        settings.K_iso_0 = 1000.0
        settings.K_iso_steep = 1000.0
        settings.iso_dslope = 4.0 / 1000.0
        settings.iso_slopec = 1.0 / 1000.0
        settings.enable_skew_diffusion = True

        settings.enable_hor_friction = True
        settings.A_h = (4 * settings.degtom) ** 3 * 2e-11
        settings.enable_hor_friction_cos_scaling = True
        settings.hor_friction_cosPower = 1

        settings.enable_implicit_vert_friction = True
        settings.enable_tke = True
        settings.c_k = 0.1
        settings.c_eps = 0.7
        settings.alpha_tke = 30.0
        settings.mxl_min = 1e-8
        settings.tke_mxl_choice = 2
        settings.kappaM_min = 2e-4
        settings.kappaH_min = 2e-5
        settings.enable_kappaH_profile = True
        settings.enable_tke_superbee_advection = True

        settings.enable_eke = True
        settings.eke_k_max = 1e4
        settings.eke_c_k = 0.4
        settings.eke_c_eps = 0.5
        settings.eke_cross = 2.0
        settings.eke_crhin = 1.0
        settings.eke_lmin = 100.0
        settings.enable_eke_superbee_advection = True

        settings.enable_idemix = False
        settings.enable_idemix_hor_diffusion = True
        settings.enable_eke_diss_surfbot = True
        settings.eke_diss_surfbot_frac = 0.2
        settings.enable_idemix_superbee_advection = True

        settings.eq_of_state_type = 5

        # custom variables
        state.dimensions["nmonths"] = 12
        forc_dim = ('xt', 'yt', 'nmonths')
        state.var_meta.update(
            sss_clim=Variable("sss_clim", ("xt", "yt", "nmonths"), "", "", time_dependent=False),
            sst_clim=Variable("sst_clim", ("xt", "yt", "nmonths"), "", "", time_dependent=False),
            qnec=Variable("qnec", ("xt", "yt", "nmonths"), "", "", time_dependent=False),
            qnet=Variable("qnet", ("xt", "yt", "nmonths"), "", "", time_dependent=False),
            taux=Variable("taux", ("xt", "yt", "nmonths"), "", "", time_dependent=False),
            tauy=Variable("tauy", ("xt", "yt", "nmonths"), "", "", time_dependent=False),

            uWind_f = Variable("Zonal wind velocity", forc_dim, "m/s"),
            vWind_f = Variable("Meridional wind velocity", forc_dim, "m/s"),
            wSpeed_f = Variable("Wind speed", forc_dim, "m/s"),
            SWDown_f = Variable("Downward shortwave radiation", forc_dim, "W/m^2"),
            LWDown_f = Variable("Downward longwave radiation", forc_dim, "W/m^2"),
            ATemp_f = Variable("Atmospheric temperature", forc_dim, "K"),
            aqh_f = Variable("Atmospheric specific humidity", forc_dim, "g/kg"),
            precip_f = Variable("Precipitation rate", forc_dim, "m/s"),
            snowfall_f = Variable("Snowfall rate", forc_dim, "m/s"),
            evap_f = Variable("Evaporation", forc_dim, "m"),
            surfPress_f = Variable("Surface pressure", forc_dim, "P"),
            meanSeaLevelPress_f = Variable("Atmospheric pressure at mean sea level", forc_dim, "P")
        )

    def _read_forcing(self, var):
        with h5netcdf.File(DATA_FILES["forcing"], "r") as infile:
            var_obj = infile.variables[var]
            return npx.array(var_obj).T

    @veros_routine
    def set_grid(self, state):
        vs = state.variables
        settings = state.settings
        if self.fine_z:
            vs.dzt = veros.tools.get_vinokur_grid_steps(settings.nz, self.max_depth, self.min_depth, refine_towards='lower')
        else:
            ddz = npx.array(
            [50.0, 70.0, 100.0, 140.0, 190.0, 240.0, 290.0, 340.0, 390.0, 440.0, 490.0, 540.0, 590.0, 640.0, 690.0]
            )
            vs.dzt = ddz[::-1]
        vs.dxt = 4.0 * npx.ones_like(vs.dxt)
        vs.dyt = 4.0 * npx.ones_like(vs.dyt)

    @veros_routine
    def set_coriolis(self, state):
        vs = state.variables
        settings = state.settings
        vs.coriolis_t = update(
            vs.coriolis_t, at[...], 2 * settings.omega * npx.sin(vs.yt[npx.newaxis, :] / 180.0 * settings.pi)
        )

    @veros_routine(dist_safe=False, local_variables=["kbot", "xt", "yt", "zt"])
    def set_topography(self, state):
        vs = state.variables
        settings = state.settings

        bathymetry_data = self._read_forcing("bathymetry")
        salt_data = self._read_forcing("salinity")[:, :, ::-1]
        zt_forc = self._read_forcing("zt")[::-1]
        salt_interp = veros.tools.interpolate((vs.xt[2:-2], vs.yt[2:-2], zt_forc), salt_data,
                                                (vs.xt[2:-2], vs.yt[2:-2], vs.zt), kind="nearest")
        if self.fine_z:
            salt = salt_interp
        else:
            salt = salt_data

        land_mask = (vs.zt[npx.newaxis, npx.newaxis, :] <= bathymetry_data[..., npx.newaxis]) | (salt == 0.0)

        vs.kbot = update(vs.kbot, at[2:-2, 2:-2], 1 + npx.sum(land_mask.astype("int"), axis=2))

        # set all-land cells
        all_land_mask = (bathymetry_data == 0) | (vs.kbot[2:-2, 2:-2] == settings.nz)
        vs.kbot = update(vs.kbot, at[2:-2, 2:-2], npx.where(all_land_mask, 0, vs.kbot[2:-2, 2:-2]))

    @veros_routine(
        dist_safe=False,
        local_variables=[
            "taux",
            "tauy",
            "qnec",
            "qnet",
            "sss_clim",
            "sst_clim",
            "temp",
            "salt",
            "area_t",
            "maskT",
            "forc_iw_bottom",
            "forc_iw_surface",
            "xt",
            "yt",
            "zt",
            "uWind_f",
            "vWind_f",
            "wSpeed_f",
            "SWDown_f",
            "LWDown_f",
            "ATemp_f",
            "aqh_f",
            "precip_f",
            "snowfall_f",
            "surfPress_f",
            "meanSeaLevelPress_f",
            "evap_f",
            "tau",
            # masks and grid
            "maskT","maskU","maskV",
            "iceMask","iceMaskU","iceMaskV","maskInC","maskInU","maskInV",
            "coriolis_t","fCori",
            "dxt","dyt","dxu","dyu",
            "dxC","dyC","dxU","dyU","dxG","dyG","dxV","dyV",
            "recip_dxC","recip_dyC","recip_dxG","recip_dyG","recip_dxU","recip_dyU","recip_dxV","recip_dyV",
            "area_t","area_u","area_v",
            "rA","rAu","rAv","rAz",
            "recip_rA","recip_rAu","recip_rAv","recip_rAz"
        ],
    )
    def set_initial_conditions(self, state):
        vs = state.variables
        settings = state.settings

        # vertical dimension of the forcing grid
        zt_forc = self._read_forcing("zt")[::-1]

        # use this function to interpolate intitial conditions with x,y, and z dimension (no time dimension) 
        def interpolate_z(data):
            return veros.tools.interpolate((vs.xt[2:-2], vs.yt[2:-2], zt_forc), data,
                                                (vs.xt[2:-2], vs.yt[2:-2], vs.zt), kind="nearest")

        # initial conditions for T and S
        temp_data = self._read_forcing("temperature")[:, :, ::-1]
        temp_interp = interpolate_z(temp_data)
        if self.fine_z:
            temp = temp_interp
        else:
            temp = temp_data
        vs.temp = update(
            vs.temp, at[2:-2, 2:-2, :, :2], temp[:, :, :, npx.newaxis] * vs.maskT[2:-2, 2:-2, :, npx.newaxis]
        )

        salt_data = self._read_forcing("salinity")[:, :, ::-1]
        salt_interp = interpolate_z(salt_data)
        if self.fine_z:
            salt = salt_interp
        else:
            salt = salt_data
        vs.salt = update(
            vs.salt, at[2:-2, 2:-2, :, :2], salt[..., npx.newaxis] * vs.maskT[2:-2, 2:-2, :, npx.newaxis]
        )

        # use Trenberth wind stress from MITgcm instead of ECMWF (also contained in ecmwf_4deg.cdf)
        vs.taux = update(vs.taux, at[2:-2, 2:-2, :], self._read_forcing("tau_x"))
        vs.tauy = update(vs.tauy, at[2:-2, 2:-2, :], self._read_forcing("tau_y"))

        # SST and SSS
        vs.sst_clim = update(vs.sst_clim, at[2:-2, 2:-2, :], self._read_forcing("sst"))
        vs.sss_clim = update(vs.sss_clim, at[2:-2, 2:-2, :], self._read_forcing("sss"))

        if settings.enable_idemix:
            vs.forc_iw_bottom = update(
                vs.forc_iw_bottom, at[2:-2, 2:-2], self._read_forcing("tidal_energy") / settings.rho_0
            )
            vs.forc_iw_surface = update(
                vs.forc_iw_surface, at[2:-2, 2:-2], self._read_forcing("wind_energy") / settings.rho_0 * 0.2
            )

        # read netcdf files
        def read_forcing(var,file):
            with netCDF4.Dataset(PATH + file) as infile:
                forcing = npx.flip(npx.squeeze(infile[var][:].T), axis=1)
            return forcing

        # veros and forcing grid
        t_grid_hor = (vs.xt[2:-2], vs.yt[2:-2], npx.arange(12))
        xt_forc = npx.array(netCDF4.Dataset(PATH + DATA_ML)['longitude'])
        yt_forc = npx.array(netCDF4.Dataset(PATH + DATA_ML)['latitude'][::-1])
        forc_grid_hor = (xt_forc, yt_forc, npx.arange(12))

        # interpolate forcing data to the veros grid
        def interpolate(forcing):
            return veros.tools.interpolate(forc_grid_hor, forcing, t_grid_hor)

        # wind velocities and speed
        vs.uWind_f = update(vs.uWind_f, at[2:-2,2:-2,:], interpolate(read_forcing('u',DATA_ML)[:,:,1,:]))
        vs.vWind_f = update(vs.vWind_f, at[2:-2,2:-2,:], interpolate(read_forcing('v',DATA_ML)[:,:,1,:]))
        vs.wSpeed_f = npx.sqrt(vs.uWind_f**2 + vs.vWind_f**2)

        # downward shortwave and longwave radiation
        vs.SWDown_f = update(vs.SWDown_f, at[2:-2,2:-2], interpolate(read_forcing('msdwswrf',DATA_SFC)))
        vs.LWDown_f = update(vs.LWDown_f, at[2:-2,2:-2], interpolate(read_forcing('msdwlwrf',DATA_SFC)))

        # atmospheric temperature and specific humidity
        vs.ATemp_f = update(vs.ATemp_f, at[2:-2,2:-2], interpolate(read_forcing('t',DATA_ML)[:,:,1,:]))
        vs.aqh_f = update(vs.aqh_f, at[2:-2,2:-2], interpolate(read_forcing('q',DATA_ML)[:,:,1,:]))

        # (convective + large scale) precipitation and snowfall rate (snowfall rate in water equivalent)
        rhoSea = 1026
        vs.precip_f = update(vs.precip_f, at[2:-2,2:-2],
            ( interpolate(read_forcing('crr',DATA_SFC)) + interpolate(read_forcing('lsrr',DATA_SFC)) ) / rhoSea )
        vs.snowfall_f = update(vs.snowfall_f, at[2:-2,2:-2],
            ( interpolate(read_forcing('csfr',DATA_SFC)) + interpolate(read_forcing('lssfr',DATA_SFC)) ) / rhoSea )

        # evaporation
        vs.evap_f = update(vs.evap_f, at[2:-2,2:-2], interpolate(read_forcing('e',DATA_SFC)) /  86400 )

        # surface pressure
        vs.surfPress_f = update(vs.surfPress_f, at[2:-2,2:-2], interpolate(read_forcing('sp',DATA_SFC)))

        # atmospheric pressure at mean sea level
        vs.meanSeaLevelPress_f = update(vs.meanSeaLevelPress_f, at[2:-2,2:-2], interpolate(read_forcing('msl',DATA_SFC)))

        ### copy the veros variables onto the versis ones

        # masks
        vs.iceMask = vs.maskT[:,:,-1]
        vs.iceMaskU = vs.maskU[:,:,-1]
        vs.iceMaskV = vs.maskV[:,:,-1]
        vs.maskInC = vs.iceMask
        vs.maskInU = vs.iceMaskU
        vs.maskInV = vs.iceMaskV

        # grid
        vs.fCori = vs.coriolis_t
        ones2d = npx.ones_like(vs.maskInC)
        vs.dxC = ones2d * vs.dxt[:,npx.newaxis]
        vs.dyC = ones2d * vs.dyt
        vs.dxU = ones2d * vs.dxu[:,npx.newaxis]
        vs.dyU = ones2d * vs.dyu

        # these are not specified in veros #TODO calculate them by averaging?
        vs.dxG = ones2d * vs.dxU
        vs.dyG = ones2d * vs.dyU
        vs.dxV = ones2d * vs.dxU
        vs.dyV = ones2d * vs.dyU

        vs.recip_dxC = 1 / vs.dxC
        vs.recip_dyC = 1 / vs.dyC
        vs.recip_dxG = 1 / vs.dxG
        vs.recip_dyG = 1 / vs.dyG
        vs.recip_dxU = 1 / vs.dxU
        vs.recip_dyU = 1 / vs.dyU
        vs.recip_dxV = 1 / vs.dxV
        vs.recip_dyV = 1 / vs.dyV

        vs.rA = vs.area_t
        vs.rAu = vs.area_u
        vs.rAv = vs.area_v
        vs.rAz = vs.rA #TODO calculate this by averaging; not specified in veros 
        vs.recip_rA = 1 / vs.rA
        vs.recip_rAu = 1 / vs.rAu
        vs.recip_rAv = 1 / vs.rAv
        vs.recip_rAz = 1 / vs.rAz

    @veros_routine
    def set_forcing(self, state):
        vs = state.variables
        vs.update(set_forcing_kernel(state))

    @veros_routine
    def set_diagnostics(self, state):
        settings = state.settings
        state.diagnostics["snapshot"].output_frequency = 86400.0
        state.diagnostics['snapshot'].output_variables += [
            'hIceMean','hSnowMean','Area','TSurf','uIce','vIce','uOcean','vOcean',
            'theta','ocSalt','Qnet','Qsw',
            'uWind','vWind','wSpeed','SWDown','LWDown','ATemp','aqh',
            'precip','snowfall','evap','fCori','runoff',
            'iceMask','iceMaskU','iceMaskV',
            'maskT','maskU','maskV',
            'forc_salt_surface','saltflux','EmPmR',
            'ssh_an','psi','dpsi',
            'os_hIceMean','os_hSnowMean',
            #TODO remove this
            'F_lh','F_lwu','F_sens','q_s','LWDown','SWDown','F_ia_net','F_io_net', 'F_oi',
            'IceGrowthRateMixedLayer','dhIceMean_dt','dArea_dt','dArea_oiFlux','dArea_oaFlux','dArea_iaFlux',
            'IceGrowthRateOpenWater','NetExistingIceGrowthRate',
            'p_hydro','u','v','R_low',
            'dxt','dyt','dxu','dyu','dzt','dzw',
            'surf_theta','TempFrz'
            ]
        state.diagnostics["overturning"].output_frequency = 360 * 86400.0
        state.diagnostics["overturning"].sampling_frequency = settings.dt_tracer
        state.diagnostics["energy"].output_frequency = 360 * 86400.0
        state.diagnostics["energy"].sampling_frequency = 86400
        average_vars = ["temp", "salt", "u", "v", "w", "surface_taux", "surface_tauy", "psi", "hIceMean"]
        state.diagnostics["averages"].output_variables = average_vars
        state.diagnostics["averages"].output_frequency = 86400.0 * 10
        state.diagnostics["averages"].sampling_frequency = 86400

    @veros_routine
    def after_timestep(self, state):
        pass

@veros_kernel
def set_forcing_kernel(state):
    vs = state.variables
    settings = state.settings

    year_in_seconds = 360 * 86400.0
    (n1, f1), (n2, f2) = veros.tools.get_periodic_interval(vs.time, year_in_seconds, year_in_seconds / 12.0, 12)

    # interpolate the monthly mean data to the value at the current time step
    def current_value(field):
        return f1 * field[:, :, n1] + f2 * field[:, :, n2]

    # wind stress
    vs.surface_taux = current_value(vs.taux)
    vs.surface_tauy = current_value(vs.tauy)

    # tke flux
    if settings.enable_tke:
        vs.forc_tke_surface = update(
            vs.forc_tke_surface,
            at[1:-1, 1:-1],
            npx.sqrt(
                (0.5 * (vs.surface_taux[1:-1, 1:-1] + vs.surface_taux[:-2, 1:-1]) / settings.rho_0) ** 2
                + (0.5 * (vs.surface_tauy[1:-1, 1:-1] + vs.surface_tauy[1:-1, :-2]) / settings.rho_0) ** 2
            )
            ** 1.5,
        )

    # surface heat flux
    qnet, qnec = heat_flux(state)

    # veros and forcing grid
    t_grid = (vs.xt, vs.yt)
    xt_forc = npx.array(netCDF4.Dataset(PATH + DATA_ML)['longitude'])
    yt_forc = npx.array(netCDF4.Dataset(PATH + DATA_ML)['latitude'][::-1])
    forc_grid = (xt_forc,yt_forc)

    def interpolate_q(q):
        return veros.tools.interpolate(forc_grid, q, t_grid)

    qnet = interpolate_q(qnet)
    qnec = interpolate_q(qnec)

    mean_flux = (
        npx.sum(qnet[2:-2, 2:-2] * vs.area_t[2:-2, 2:-2]) / 12 / npx.sum(vs.area_t[2:-2, 2:-2])
    )
    logger.info(" removing an annual mean heat flux imbalance of %e W/m^2" % mean_flux)
    qnet = (qnet - mean_flux) * vs.maskT[:, :, -1]

    # heat flux : W/m^2 K kg/J m^3/kg = K m/s
    cp_0 = 3991.86795711963
    sst = f1 * vs.sst_clim[:, :, n1] + f2 * vs.sst_clim[:, :, n2]
    vs.forc_temp_surface = (
        (qnet + qnec * (sst - vs.temp[:, :, -1, vs.tau])) * vs.maskT[:, :, -1] / cp_0 / settings.rho_0
    )

    # the salt flux is calculated in the growth routine of versis

    # wind velocities and speed
    vs.uWind = current_value(vs.uWind_f)
    vs.vWind = current_value(vs.vWind_f)
    vs.wSpeed = npx.sqrt(vs.uWind**2 + vs.vWind**2)

    # downward shortwave and longwave radiation
    vs.SWDown = current_value(vs.SWDown_f)
    vs.LWDown = current_value(vs.LWDown_f)

    # atmospheric temperature and specific humidity
    vs.ATemp = current_value(vs.ATemp_f)
    vs.aqh = current_value(vs.aqh_f)

    # (convective + large scale) precipitation and snowfall rate (snowfall rate in water equivalent)
    vs.precip = current_value(vs.precip_f)
    vs.snowfall = current_value(vs.snowfall_f)

    # evaporation
    vs.evap = current_value(vs.evap_f)

    # surface pressure
    vs.surfPress = current_value(vs.surfPress_f)

    # calculate sea surface height anomaly from surface pressure anomaly
    rhoSea = 1026
    gravity = 9.81
    meanSeaLevelPress = current_value(vs.meanSeaLevelPress_f)
    vs.ssh_an = ( meanSeaLevelPress - vs.surfPress ) / ( rhoSea * gravity )


    return KernelOutput(
        surface_taux=vs.surface_taux,
        surface_tauy=vs.surface_tauy,
        forc_tke_surface=vs.forc_tke_surface,
        forc_temp_surface=vs.forc_temp_surface,
        forc_salt_surface=vs.forc_salt_surface,
        uWind = vs.uWind,
        vWind = vs.vWind,
        wSpeed = vs.wSpeed,
        SWDown = vs.SWDown,
        LWDown = vs.LWDown,
        ATemp = vs.ATemp,
        aqh = vs.aqh,
        precip = vs.precip,
        snowfall = vs.snowfall,
        evap = vs.evap,
        surfPress = vs.surfPress,
        ssh_an = vs.ssh_an
    )