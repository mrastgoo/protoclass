#title           :texture_analysis.py
#description     :This will create a header for a python script.
#author          :Guillaume Lemaitre
#date            :2015/04/20
#version         :0.1
#notes           :
#python_version  :2.7.6  
#==============================================================================

# Import the needed libraries
# Numpy library
import numpy as np
# Scikit-learn
### Module to extract 2D patches
from sklearn.feature_extraction import image
# Mahotas library
### Module to extract haralick features
from mahotas.features import haralick
# Joblib library
### Module to performed parallel processing
from joblib import Parallel, delayed
# Multiprocessing library
import multiprocessing
# Operator library
import operator

def HaralickMapExtraction(im, **kwargs):
    """Function to extract the Haralick map from a 2D or 3D image

    Parameters
    ----------
    im: ndarray of int
        2D or 3D array containing the image information
    win_size: tuple (optional)
        Tuple containing 2 or 3 values defining the window size
        to consider during the extraction
    n_gray_levels: int (optional)
        Number of gray level to use to rescale the original image
    gray_limits: tuple (optional)
        Tuple containing 2 values defining the minimum and maximum
        gray level.

    Returns
    -------
    maps: ndarray of np.double
        If 2D image - maps is of size 4 x 14 x image height x image width)
        which will contain the map corresponding to the different 
        orientations and statistic of Haralick features.
    
    """
    
    # Check the dimension of the input image
    if len(im.shape) == 2:
        nd_im = 2
        win_size = kwargs.pop('win_size', (7, 7))
    elif len(im.shape) == 3:
        nd_im = 3
        win_size = kwargs.pop('win_size', (7, 7, 7))
    else:
        raise ValueError('mahotas.texture.haralick: Can only handle 2D and 3D images.')

    n_gray_levels = kwargs.pop('n_gray_levels', np.max(im))
    gray_limits = kwargs.pop('gray_limits', (float(np.min(im)), float(np.max(im))))

    # Check that win_size is a tuple
    if not isinstance(gray_limits, tuple):
        raise ValueError('gray_limits has to be a tuple with 2 values characterizing the extrmum use in the rescaling.')

    # Check that the minimum is inferior to the maximum
    if gray_limits[0] > gray_limits[1]:
        raise ValueError('gray_limits[0] > gray_limits[1]: Inverse the order in the tuple such as (min_int, max_int).')
    
    # Check that win_size is a tuple
    if not isinstance(win_size, tuple):
        raise ValueError('win_size has to be a tuple with 2 or 3 values depending of the image.')

    # Check that nd_im is of the same dimension than win_size
    if nd_im != len(win_size):
        raise ValueError('The dimension of the image do not agree with the window size dimensions: 2D - 3D')
    
    # Rescale the image
    ### Define a lambda function for that
    ImageRescaling = lambda im : np.around((im.astype(float) - gray_limits[0]) * (float(n_gray_levels) / (gray_limits[1] - gray_limits[0])))
    im_rescale = ImageRescaling(im).astype(int)
    
    # Call the 2D patch extractors
    if nd_im == 2:
        # Extract the patches to analyse
        patches = ExtractPatches2D(im_rescale, win_size)
        # Compute the Haralick maps
        i_h, i_w = im_rescale.shape[:2]
        p_h, p_w = win_size[:2]
        n_h = i_h - p_h + 1
        n_w = i_w - p_w + 1
        maps = BuildMaps2D(patches, (n_h, n_w))
    
    return maps

def HaralickProcessing(patch_in):
    """Function to compute Haralick for a patch

    Parameters
    ----------
    patch_in: ndarray of int
        2D or 3D array containing the image information

    Returns
    -------
    hara_fea: ndarray of np.double
        A 4x13 or 4x14 feature vector (one row per direction) if `f` is 2D,
        13x13 or 13x14 if it is 3D. The exact number of features depends on the
        value of ``compute_14th_feature`` Also, if either ``return_mean`` or
        ``return_mean_ptp`` is set, then a single dimensional array is
        returned.
    
    """
    
    # Compute Haralick feature
    return haralick(patch_in)

########################################################################################
### 2D implementation

def ExtractPatches2D(im, win_size):
    """Function to extract the 2D patches which which will feed haralick

    Parameters
    ----------
    im: ndarray
        2D array containing the image information
    win_size: tuple
        Array containing 2 values defining the window size in order to 
        perform the extraction

    Returns
    -------
    patches: array, shape = (n_patches, patch_height, patch_width)
        The collection of patches extracted from the image.
    
    """

    if len(im.shape) != 2:
        raise ValueError('extraction.Extract2DPatches: The image can only be a 2D image.')
    if len(win_size) != 2:
        raise ValueError('extraction.Extract2DPatches: The win_size can only be a tuple with 2 values.')

    return image.extract_patches_2d(im, win_size)

def BuildMaps2D(patches, im_shape):
    """Function to compute Haralick features for all patch

    Parameters
    ----------
    patches: array, shape = (n_patches, patch_height, patch_width)
        The collection of patches extracted from the image.

    Returns
    -------
    maps: ndarray of np.double
        If 2D image - maps is of size 4 x 14 x image height x image width)
        which will contain the map corresponding to the different 
        orientations and statistic of Haralick features.
    
    """

    # Compute the Haralick statistic in parallel
    num_cores = multiprocessing.cpu_count()
    patch_arr = Parallel(n_jobs=num_cores)(delayed(HaralickProcessing)(p) for p in patches)

    # Convert the patches into maps
    return ReshapePatchsToMaps2D(patch_arr, im_shape)

def ReshapePatchsToMaps2D(patches_haralick, im_shape):
    """Function to reshape the array of patches into proper maps

    Parameters
    ----------
    patches: list of array, shape = (n_patches, 4 orientations, 14 features)
        See HaralickProcessing() for the justification of the shape.

    Returns
    -------
    maps: ndarray of np.double
        If 2D image - maps is of size 4 x 14 x image height x image width)
        which will contain the map corresponding to the different 
        orientations and statistic of Haralick features.
    
    """

    # Conver the list into a numpy array
    patches_numpy = np.array(patches_haralick)

    # Get the current size
    n_patch, n_orientations, n_statistics = patches_numpy.shape

    # Reshape the patches into a map first
    maps = patches_numpy.reshape((im_shape[0], im_shape[1], n_orientations, n_statistics))

    # Swap the good dimension in order to have [Orientation][Statistic][Y, X]
    maps = maps.swapaxes(0, 2)
    maps = maps.swapaxes(1, 3)

    # We would like to have a list for the orientations and a list for the statistics 
    return maps
