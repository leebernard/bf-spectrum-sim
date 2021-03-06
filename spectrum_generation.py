"""
This is for generating a simulated spectrum

Current goal is to take a 1-D high resolution solar spectrum, and resample it to lower pixels per
angstrom using interpolation. Then the spectrum will be mapped out to a 2-D pattern, to simulate an
idealized output from a spectrograph
"""

import numpy as np
import matplotlib.pyplot as plt
import sys
import galsim

from astropy.io import fits
# from astropy.modeling import models, fitting
from scipy.ndimage import gaussian_filter
from scipy.ndimage import gaussian_filter1d
# from scipy.ndimage import convolve1d
# from scipy.ndimage.filters import _gaussian_kernel1d
# from scipy import integrate
from spectrum_fitter import spectrum_gaussian_fit


from toolkit import spectrum_slicer

# set if the plots will display or not
display = False

with fits.open('sun.fits') as hdul:
    # hdul = fits.open('sun.fits')
    sun = hdul[0].copy()

    angstrom_per_pix = sun.header['CDELT1']
    intial_angstrom = sun.header['CRVAL1']

# generate an x-data set
angstrom = np.arange(0, sun.data.size, step=1) * angstrom_per_pix + intial_angstrom

# '''
# filter_factor = 10
# x = np.linspace(-5*np.pi, 5*np.pi, num=sun_slice.size)  # generate values over 10 periods
# sinc_kernel = np.sinc(x*filter_factor)
# # normalize the kernal
# sinc_kernel = sinc_kernel/np.sum(sinc_kernel)

'''
# this is just test data, to check the kernel the filter is using
lw = int(4.0 * float(sigma) + 0.5)
gauss_kernel = _gaussian_kernel1d(sigma, order=0, radius=lw)
'''


# filter the full spectrum
# the 1/.002 accounts for the spacing being .002
resolution = 500  # 1/.002  # the resolution of the spectrum in angstroms. This corresponds to FWHM
sigma = resolution/(2.0 * np.sqrt(2.0 * np.log(2.0)))
filtered_sun = gaussian_filter(sun.data, sigma)

if display:
    plt.figure('Full available solar spectrum')
    plt.scatter(angstrom, sun.data, s=1)
    plt.scatter(angstrom, filtered_sun, s=1)
    plt.title('Slice of Solar spectrum')
    plt.xlabel('Angstroms')
    plt.legend(['Before smoothing', 'After smoothing'])

    # find a slice of data
    start_ang = 5450
    end_ang = 5460
    angstrom_slice, sun_slice = spectrum_slicer(start_ang, end_ang, angstrom, filtered_sun)

    plt.figure('Slice of Filtered Solar Spectrum')
    plt.scatter(angstrom_slice, sun_slice, s=1)
    # plt.xlim(5000, 5500)
    # plt.xlim(5500, 6000)
    # plt.xlim(6000, 6500)
    # plt.xlim(6500, 7000)
    # plt.xlim(7000, angstrom[-1])

    plt.xlim(5400, 5500)  # fairly isolated feature at 5455.6 angs, prob a Fe I line
    # plt.xlim(5454, 5457)


'''bin the 1D data into pixels'''

# take a slice of data
start_ang = 6540
end_ang = 6580
# start_ang = 5450
# end_ang = 5460
angstrom_slice, sun_slice = spectrum_slicer(start_ang, end_ang, angstrom, filtered_sun)

sim_angstroms_per_pixel = .35  # resolution of the simlulated pixel grid
bin_factor = int(sim_angstroms_per_pixel/angstrom_per_pix)

excess_data_index = int(sun_slice.size % bin_factor)
if excess_data_index:
    angstrom_slice = angstrom_slice[:-excess_data_index]
    sun_slice = sun_slice[:-excess_data_index]

binned_angstroms = np.reshape(angstrom_slice, (int(angstrom_slice.size/bin_factor), bin_factor))
binned_spectrum = np.reshape(sun_slice, (int(sun_slice.size/bin_factor), bin_factor))

binned_angstroms = np.mean(binned_angstroms, axis=1)
binned_spectrum = np.sum(binned_spectrum, axis=1) * sim_angstroms_per_pixel

if display:
    plt.figure('Pixeled data')
    plt.bar(binned_angstroms, binned_spectrum)


'''2D spectrum'''

# expand the array, using gausssian
num_spacial_pixels = int(10/sim_angstroms_per_pixel)
spectrum2d = np.insert(np.zeros((num_spacial_pixels, binned_spectrum.size)),  # generate an array of zeros
                       int(num_spacial_pixels/2),                               # location to insert data, the middle
                       binned_spectrum,                                       # spectrum to be inserted
                       axis=0)                                             # axis the spectrum is inserted along

smeared_spectrum2d = gaussian_filter1d(spectrum2d, sigma=4, axis=0)

"""
# expand the array, making a tophat
num_spacial_pixels = int(8)
tophat_width = 11

spectrum2d = np.zeros((num_spacial_pixels, binned_spectrum.size))  # loop lead-in
for n in range(4):
    spectrum2d = np.insert(spectrum2d,  # generate an array of zeros
                           int(num_spacial_pixels / 2),  # location to insert data, the middle
                           binned_spectrum,  # spectrum to be inserted
                           axis=0)
smeared_spectrum2d = spectrum2d
"""

# sys.getsizeof(smeared_spectrum2d)

"""
x_lower = 10000
x_upper = 10500
plt.figure('unsmeared spectrum')
plt.imshow(spectrum2d, cmap='viridis')
# plt.xlim(x_lower, x_upper)

plt.figure('smeared spectrum')
# from matplotlib.colors import LogNorm
plt.imshow(smeared_spectrum2d, cmap='viridis')
# plt.xlim(x_lower, x_upper)

plt.show()
"""

nobf_filename = 'spectrum_sim_gausshalf_bffalse.fits'
yesbf_filename = 'spectrum_sim_gausshalf_bftrue.fits'

rng = galsim.BaseDeviate(5678)

# multiply the total flux by a scalar
scalar = 0.5
# transform the spectrum image into a galsim object
spectrum_image = galsim.Image(smeared_spectrum2d * scalar, scale=1.0)  # scale is pixel/pixel
# interpolate the image so GalSim can manipulate it
spectrum_interpolated = galsim.InterpolatedImage(spectrum_image)
spectrum_interpolated.drawImage(image=spectrum_image,
                                method='phot',
                                # center=(15, 57),
                                sensor=galsim.Sensor())

print('image center:', spectrum_image.center)
print('image true center:', spectrum_image.true_center)
spectrum_image.write(nobf_filename)
if display:
    galsim_sensor_image = spectrum_image.array.copy()


# now do it again, but with the BF effect
# spectrum_image = galsim.Image(smeared_spectrum2d, scale=.25)  # scale is angstroms/pixel
# interpolate the image so GalSim can manipulate it
# spectrum_interpolated = galsim.InterpolatedImage(spectrum_image)

spectrum_interpolated.drawImage(image=spectrum_image,
                                method='phot',
                                # center=(15,57),                               
                                offset=(0, 0),  # this needs 4 digits
                                sensor=galsim.SiliconSensor(name='lsst_e2v_50_32',
                                                            transpose=False,
                                                            rng=rng,
                                                            diffusion_factor=0.0))

print('image center:', spectrum_image.center)
print('image true center:', spectrum_image.true_center)
spectrum_image.write(yesbf_filename)
if display:
    galsim_bf_image = spectrum_image.array.copy()

''' block comment out the center correction
 apparently the correction is flux dependant, and therefore part of the data
"""Measure the offset between the two data sets:"""
with fits.open(nobf_filename) as hdul:
    galsim_sensor_image = hdul[0].data

    with fits.open(yesbf_filename) as hdul:
        galsim_bf_image = hdul[0].data

        # take an average profile
        np.std(galsim_sensor_image[14, 15:30])  # center row, relatively flat area in spectrum
        np.mean(galsim_sensor_image[14, 15:30])

        mean_sensor_profile = np.mean(galsim_sensor_image[:, 15:30], axis=1)
        mean_nobf_pixels = np.arange(mean_sensor_profile.size)
        mean_bf_profile = np.mean(galsim_bf_image[:, 15:30], axis=1)
        mean_bf_pixels = np.arange(mean_bf_profile.size)

        # fit the profiles
        g_nobf, nobf_fitter = spectrum_gaussian_fit(mean_nobf_pixels, mean_sensor_profile, amplitude=50000., mean=14.,
                                                    stddev=1.)
        g_withbf, withbf_fitter = spectrum_gaussian_fit(mean_bf_pixels, mean_bf_profile, amplitude=50000., mean=14.,
                                                        stddev=1.)
        print('Fit Results:')
        print('No bf:', g_nobf.parameters)
        print('With bf', g_withbf.parameters)
        mean_difference = g_nobf.parameters[1] - g_withbf.parameters[1]
        print('Difference in mean:', mean_difference)

"""Run the simulation again, with the correction"""
spectrum_interpolated.drawImage(image=spectrum_image,
                                method='phot',
                                # center=(15, 57),
                                sensor=galsim.Sensor())

print('image center:', spectrum_image.center)
print('image true center:', spectrum_image.true_center)
spectrum_image.write(nobf_filename)
galsim_sensor_image = spectrum_image.array.copy()


# now do it again, but with the BF effect
# spectrum_image = galsim.Image(smeared_spectrum2d, scale=.25)  # scale is angstroms/pixel
# interpolate the image so GalSim can manipulate it
# spectrum_interpolated = galsim.InterpolatedImage(spectrum_image)

spectrum_interpolated.drawImage(image=spectrum_image,
                                method='phot',
                                # center=(15,57),
                                offset=(0, mean_difference),  # this needs 4 digits
                                sensor=si_sensor)

print('image center:', spectrum_image.center)
print('image true center:', spectrum_image.true_center)
spectrum_image.write(yesbf_filename)
galsim_bf_image = spectrum_image.array.copy()

# end comment out
'''

if display:
    difference_image = galsim_bf_image[:, 5:-5] - galsim_sensor_image[:, 5:-5]

    plt.figure('GalSim image', figsize=(8, 12))
    plt.subplot(311)
    plt.imshow(galsim_sensor_image[:, 5:-5], cmap='viridis')
    plt.title('H-alpha line, ideal sensor')
    plt.colorbar()

    plt.subplot(312)
    plt.imshow(galsim_bf_image[:, 5:-5], cmap='viridis')
    plt.title('H-alpha line, with sensor noise')
    plt.colorbar()

    # plt.figure('Noise Image - Ideal Image')
    plt.subplot(313)
    plt.imshow(difference_image, cmap='viridis')
    plt.title('Residuals: Noise Image - Ideal Image')
    plt.colorbar()

    plt.figure('slice at row 15', figsize=(8, 6))
    row = 20
    plt.subplot(311)
    plt.title('original data')
    plt.plot(smeared_spectrum2d[row])
    plt.subplot(312)
    plt.title('Sensor sim')
    plt.plot(galsim_sensor_image[row])
    plt.subplot(313)
    plt.title('Sensor with BF sim')
    plt.plot(galsim_bf_image[row])

    plt.show()


