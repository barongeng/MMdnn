from collections import namedtuple
import math

TensorShape = namedtuple('TensorShape', ['batch_size', 'channels', 'height', 'width'])


def get_filter_output_shape(i_h, i_w, params, round_func):
    o_h = (i_h + 2 * params.p_h - params.k_h) / float(params.s_h) + 1
    o_w = (i_w + 2 * params.p_w - params.k_w) / float(params.s_w) + 1
    return (int(round_func(o_h)), int(round_func(o_w)))


def get_strided_kernel_output_shape(node, round_func):
    assert node.layer is not None
    input_shape = node.get_only_parent()[0].output_shape
    params = node.kernel_parameters
    o_h, o_w = get_filter_output_shape(input_shape.height, input_shape.width,
                                       params, round_func)
    params = node.parameters
    has_c_o = hasattr(params, 'num_output')
    c = params.num_output if has_c_o else input_shape.channels
    return TensorShape(input_shape.batch_size, c, o_h, o_w)


def shape_not_implemented(node):
    raise NotImplementedError


def shape_identity(node):
    assert len(node.parents) > 0
    return node.parents[0][0].output_shape


def shape_scalar(node):
    return TensorShape(1, 1, 1, 1)


def shape_data(node):
    if node.output_shape:
        # Old-style input specification
        return node.output_shape
    try:
        # New-style input specification
        return tuple(map(int, node.parameters.shape[0].dim))
    except:
        # We most likely have a data layer on our hands. The problem is,
        # Caffe infers the dimensions of the data from the source (eg: LMDB).
        # We want to avoid reading datasets here. Fail for now.
        # This can be temporarily fixed by transforming the data layer to
        # Caffe's "input" layer (as is usually used in the "deploy" version).
        # TODO: Find a better solution for this.
        pass


def shape_mem_data(node):
    params = node.parameters
    return TensorShape(params.batch_size, params.channels, params.height, params.width)


def shape_concat(node):
    axis = node.parameters.axis
    output_shape = None
    for parent, idx in node.parents:
        if output_shape is None:
            output_shape = list(parent.output_shape)
        else:
            output_shape[axis] += parent.output_shape[axis]
    return tuple(output_shape)


def shape_convolution(node):
    return get_strided_kernel_output_shape(node, math.floor)


def shape_pool(node):
    return get_strided_kernel_output_shape(node, math.ceil)


def shape_inner_product(node):
    input_shape = node.get_only_parent()[0].output_shape
    return TensorShape(input_shape.batch_size, node.parameters.num_output, 1, 1)