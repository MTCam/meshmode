from __future__ import division, absolute_import

__copyright__ = "Copyright (C) 2010,2012,2013 Andreas Kloeckner, Michael Tom"

__license__ = """
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import numpy as np
import numpy.linalg as la
from pytools.spatial_btree import SpatialBinaryTreeBucket
from six.moves import range


# {{{ make_element_lookup_tree

def make_element_lookup_tree(mesh, eps=1e-12):
    from meshmode.mesh.processing import find_bounding_box
    bbox_min, bbox_max = find_bounding_box(mesh)
    bbox_min -= eps
    bbox_max += eps

    tree = SpatialBinaryTreeBucket(bbox_min, bbox_max)

    for igrp, grp in enumerate(mesh.groups):
        for iel_grp in range(grp.nelements):
            el_vertices = mesh.vertices[:, grp.vertex_indices[iel_grp]]

            el_bbox_min = np.min(el_vertices, axis=-1) - eps
            el_bbox_max = np.max(el_vertices, axis=-1) + eps

            tree.insert((igrp, iel_grp), (el_bbox_min, el_bbox_max))

    return tree

# }}}


# {{{ nd_quad_submesh

def nd_quad_submesh(node_tuples):
    """Return a list of tuples of indices into the node list that
    generate a tesselation of the reference element.

    :arg node_tuples: A list of tuples *(i, j, ...)* of integers
        indicating node positions inside the unit element. The
        returned list references indices in this list.

        :func:`pytools.generate_nonnegative_integer_tuples_below`
        may be used to generate *node_tuples*.

    See also :func:`modepy.tools.simplex_submesh`.
    """

    from pytools import single_valued, add_tuples
    dims = single_valued(len(nt) for nt in node_tuples)

    node_dict = dict(
            (ituple, idx)
            for idx, ituple in enumerate(node_tuples))

    from pytools import generate_nonnegative_integer_tuples_below as gnitb

    result = []
    for current in node_tuples:
        try:
            result.append(tuple(
                    node_dict[add_tuples(current, offset)]
                    for offset in gnitb(2, dims)))

        except KeyError:
            pass

    return result

# }}}


# {{{ random rotation matrix

def rand_rotation_matrix(ambient_dim, deflection=1.0, randnums=None):
    """Creates a random rotation matrix.

    :arg deflection: the magnitude of the rotation. For 0, no rotation; for 1,
        competely random rotation. Small deflection => small perturbation.
    :arg randnums: 3 random numbers in the range [0, 1]. If `None`, they will be
        auto-generated.
    """
    # from http://www.realtimerendering.com/resources/GraphicsGems/gemsiii/rand_rotation.c  # noqa: E501
    # from http://blog.lostinmyterminal.com/python/2015/05/12/random-rotation-matrix.html  # noqa: E501

    if ambient_dim != 3:
        raise NotImplementedError("ambient_dim=%d" % ambient_dim)

    if randnums is None:
        randnums = np.random.uniform(size=(3,))

    theta, phi, z = randnums

    theta = theta * 2.0*deflection*np.pi  # Rotation about the pole (Z).
    phi = phi * 2.0*np.pi  # For direction of pole deflection.
    z = z * 2.0*deflection  # For magnitude of pole deflection.

    # Compute a vector V used for distributing points over the sphere
    # via the reflection I - V Transpose(V).  This formulation of V
    # will guarantee that if x[1] and x[2] are uniformly distributed,
    # the reflected points will be uniform on the sphere.  Note that V
    # has length sqrt(2) to eliminate the 2 in the Householder matrix.

    r = np.sqrt(z)
    Vx, Vy, Vz = V = (
        np.sin(phi) * r,
        np.cos(phi) * r,
        np.sqrt(2.0 - z)
        )

    st = np.sin(theta)
    ct = np.cos(theta)

    R = np.array(((ct, st, 0), (-st, ct, 0), (0, 0, 1)))  # noqa: N806

    # Construct the rotation matrix  ( V Transpose(V) - I ) R.

    M = (np.outer(V, V) - np.eye(3)).dot(R)  # noqa: N806
    return M

# }}}


# {{{ AffineMap

class AffineMap(object):
    """An affine map ``A@x+b``represented by a matrix *A* and an offset vector *b*.

    .. attribute:: matrix

        A :class:`numpy.ndarray` representing the matrix *A*.

    .. attribute:: offset

        A :class:`numpy.ndarray` representing the vector *b*.

    .. autofunction:: inverted
    .. autofunction:: __call__
    """

    def __init__(self, matrix, offset):
        self.matrix = matrix
        self.offset = offset

    def inverted(self):
        return AffineMap(la.inv(self.matrix), -la.solve(self.matrix, self.offset))

    def __call__(self, vecs):
        """Apply the affine map to an array *vecs* whose first axis
        length matches ``matrix.shape[1]``.
        """
        return (np.dot(self.matrix, vecs).T + self.offset).T

# }}}

# vim: foldmethod=marker
