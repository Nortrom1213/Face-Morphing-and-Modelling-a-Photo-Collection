import numpy as np
import matplotlib
import matplotlib.animation as animation
import matplotlib.pyplot as plt
import skimage as sk
import skimage.io as skio
import skimage.data as data
import skimage.transform as sktr
from skimage.draw import polygon
from scipy.spatial import Delaunay
import os
import glob
import numpy as np
import cv2
import pdb
import time
from sklearn.decomposition import PCA
from sklearn.neighbors import KDTree
import sys


IMG_SHAPE = (750, 600)
NUM_POINTS = 33

def define_points(num_points, image):
    plt.imshow(image)
    print("Select %d points." % num_points)
    points = np.array(plt.ginput(num_points, timeout=0))
    plt.close()
    return points

# read img
target = plt.imread('depp.jpg')
source = plt.imread('me.jpg')
target = sk.transform.resize(target, IMG_SHAPE)
source = sk.transform.resize(source, IMG_SHAPE)
# select points
if os.path.exists('target_points.npy'):
    target_points = np.load('target_points.npy')
    source_points = np.load('source_points.npy')
else:
    target_points = define_points(NUM_POINTS, target)
    source_points = define_points(NUM_POINTS, source)
    # save points
    np.save("target_points.npy", target_points)
    np.save("source_points.npy", source_points)


corners = np.array([
    [0, 0],
    [IMG_SHAPE[1]-1, 0],
    [0, IMG_SHAPE[0]-1],
    [IMG_SHAPE[1]-1, IMG_SHAPE[0]-1]
])
target_points = np.vstack([target_points, corners])
source_points = np.vstack([source_points, corners])


# triangulation
mid_points = (target_points + source_points)/2
triangulation = Delaunay(mid_points)

plt.figure(figsize=(20, 10))
for i, (img, points) in enumerate(zip((target, source), (target_points, source_points))):
    plt.subplot(1, 2, i+1)
    plt.imshow(img)
    plt.triplot(points[:,0], points[:,1], triangulation.simplices)
    plt.plot(points[:,0], points[:,1], 'o')

plt.savefig('triangulation.jpg')


def computeAffine(tri1_pts, tri2_pts):
    def trans(points):
        v1 = np.reshape((points[1] - points[0]), (2, 1))
        v2 = np.reshape((points[2] - points[0]), (2, 1))
        mat = np.hstack([v1, v2, np.resize(points[0], (2, 1))])
        mat = np.vstack([mat, np.array([[0, 0, 1]])])
        return mat

    return np.dot(trans(tri2_pts), np.linalg.inv(trans(tri1_pts)))


def compute_masks(target, source, target_points, source_points, triangulation, warp_frac, dissolve_frac):
    if warp_frac < 0 or warp_frac > 1 or dissolve_frac < 0 or dissolve_frac > 1:
        return None

    masks = [np.zeros((IMG_SHAPE[0], IMG_SHAPE[1], 3)) for _ in range(3)]
    mid_pts = source_points + warp_frac * (target_points - source_points)

    for tri_index in triangulation.simplices:
        mid_tri = mid_pts[tri_index]
        rr, cc = polygon(mid_tri[:, 0], mid_tri[:, 1])
        mid_xys = np.array([rr, cc])
        tmp = np.vstack([mid_xys, np.ones((1, mid_xys.shape[1]))])

        src1_tri = target_points[tri_index]
        mat_T1 = np.linalg.inv(computeAffine(src1_tri, mid_tri))
        src1_xys = np.dot(mat_T1, tmp).astype(int)
        masks[0][mid_xys[1], mid_xys[0]] = target[src1_xys[1], src1_xys[0]]

        src2_tri = source_points[tri_index]
        mat_T2 = np.linalg.inv(computeAffine(src2_tri, mid_tri))
        src2_xys = np.dot(mat_T2, tmp).astype(int)
        masks[2][mid_xys[1], mid_xys[0]] = source[src2_xys[1], src2_xys[0]]

    masks[1] = masks[2] + dissolve_frac * (masks[0] - masks[2])
    return masks


plt.figure(figsize=(15, 5))
masks = compute_masks(target, source, target_points, source_points, triangulation, 0.5, 0.5)
for i in range(3):
    plt.subplot(1, 3, i + 1)
    plt.imshow(masks[i])
plt.savefig('midway_face.jpg')

NUM_FRAMES = 45

def morph(im1, im2, pts1, pts2, tri, warp_frac, dissolve_frac):
    return compute_masks(target, source, target_points, source_points, triangulation, x, x)[1]

# generate morphing
results = []
fig = plt.figure(figsize=(8, 10))
for x in np.linspace(0, 1, NUM_FRAMES):
    img = morph(target, source, target_points, source_points, triangulation, x, x)
    img = plt.imshow(img, animated=True)
    results.append([img])

# generate animation and save
vid = animation.ArtistAnimation(
    fig,
    results,
    interval=100,
    blit=True,
    repeat_delay=1000
)
vid.save('morphing.gif', fps=30)
vid.save('morphing_slowmo.gif', fps=10)