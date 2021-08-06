---
title: Faster-RCNN,看这一篇就够了！
date: 2019-12-17 11:55:13
tags:
mathjax: true
summary: FasterRCNN网络介绍
---

本文将详细介绍著名的目标检测网络FasterRCNN，其网络结构如下图所示：

![](https://i.imgur.com/ZgZvGOb.png)

可以看到，FasterRCNN网络由`RPN网络`及`RCNN`网络组成，下面分别介绍二者的作用及网络结构。

# RPN网络

RPN网络包括提取特征的骨干网络及进行分类和回归的两个分支。分类分支的作用是预测出可能包含目标的区域而回归分支的作用是回归出包含目标区域的准确坐标。

要预测出目标区域，首先要定义目标区域。在FasterRCNN之前采用的方法有两种：

1. Opencv AdaBoost通过滑动窗口及图像金字塔生成大量区域，然后对这些区域进行分类和回归；
2. R-CNN使用Selective Search的方法选出目标区域。

FasterRCNN则是创造性的提出了Anchor的概念，也即在图像中生成大量的Anchor，然后利用神经网络对Anchor进行分类和回归。

![](https://i.imgur.com/YR2kXUN.jpg)

## Anchor的生成与使用

![](https://i.imgur.com/qeNWvAc.jpg)

Faster RCNN在生成的特征图上的每个点都应用9个anchor作为初始的检测框，九个anchor为三种不同比例的检测框，分别为1:1,1:2,2:1。原图800x600，VGG下采样16倍，feature map每个点设置9个Anchor，所以共有

$$
\lceil (800/16) \rceil \times \lceil (600/16) \rceil \times 9 = 50 \times 38 \times 9 = 17100
$$

个检测框。

## Softmax 判定anchor

利用Backbone提取特征图后，首先利用Conv1x1卷积得到一个$H\times W\times18$的矩阵，表示每个像素点处的9个anchor是正例还是负例。通过Softmax判定是否包含目标，一般认为正例包含目标。

~~~yaml
layer {
  name: "rpn_cls_score"
  type: "Convolution"
  bottom: "rpn/output"
  top: "rpn_cls_score"
  param { lr_mult: 1.0 }
  param { lr_mult: 2.0 }
  convolution_param {
    num_output: 18   # 2(bg/fg) * 9(anchors)
    kernel_size: 1 pad: 0 stride: 1
    weight_filler { type: "gaussian" std: 0.01 }
    bias_filler { type: "constant" value: 0 }
  }
}
~~~

至于Softmax之前的reshape层是用来将输入$B\times H\times W\times 18$ reshape成$B\times 2\times 9*H\times W$,第二个维度用于存放每个像素处9个anchor的Softmax分类结果，之后的reshape层是用于将其调整回$B\times 18\times H\times W$。

## RPN的Target生成

对Anchor进行分类，以下两种情况为正例：

1. 遍历Groundtruth，找到IOU最大的Anchor
2. 遍历Anchor找到与Groundtruth的IOU>0.7的值

注：一个BBOX可能使多个Anchor为正例

以下两种情况为负例：

1. 遍历所有Groundtruth和Anchor，二者之间IOU<0/3的为负例
2. 既不是正例也不是负例的其他Anchor

为每个anchor分配类别标签和GroundTruth的坐标过程给你如下：

1. 根据Anchor是否超出图像范围剔除无效的Anchor
2. 计算所有有效的Anchor与所有GroundTruth的IOU
3. 为每个GroundTruth找到与之最大IOU的Anchor的位置及IOU大小
4. 为每个Anchor找到与之IOU最大的GroundTruthr的位置及IOU大小
5. 根据4得到的Anchor最大IOU，为大于0.7的Anchor设置为正例，小于0.3的Anchor设置为负例
6. 根据3将具有最大IOU的Anchor设置为正例

在训练过程中，为了防止正负例不均衡，通常随机采样256个Anchor，其中正例负例之比为1：1。这里采样的256个Anchor仅用于训练，Proposal的输入是RPN网络的全部输出。

## Bouond box regression

Bounding box回归是为了微调检测框的位置，因为一个Anchor不可能恰好包含一个物体，因此需要对其进行调整。

假设窗口用一个4维向量(x,y,h,w)，分别代表窗口的中心点坐标，高度和宽度。给定anchor $A=(A_x, A_y, A_h, A_w)$和GroundTruth $G=(G_x, G_y, G_h, G_w)$, 则检测框回归的任务是找到一个变换$G' = F(A)$使得$G'\approx G$

这个变换的网络是在RCNN中提出的，变换F包括四个函数$F = \{d_x(A), d_y(A),d_h(A),d_w(A)\}$,分别用于对中心点做平移变换，对宽和高进行放缩：

$$
\begin{aligned}
  G'_x &= A_w d_x(A) + A_x \\\\\\
  G'_y &= A_h d_y(A) + A_y \\\\\\
  G'_w &= A_w \text{exp}(d_w(A_w)) \\\\\\
  G'_h &= A_h \text{exp}(d_h(A_h))
\end{aligned}
$$

这个回归函数的输入是特征图和GroundTruth与anchor的偏移，输出为$d_*(A), *\in\{x,y,w,h\}$.假设输入的特征图为$\phi(A)$,则：

$$
d_*(A) = W_*^T\phi(A)
$$

则损失函数为：

$$
Loss = \sum_i^N | t_*^i - W_*^T\phi(A) |
$$

其中，$t_*$为GroundTruth与anchor之间的偏移，具体为：

<div>
$$
\begin{aligned}
  t_x = \frac{G_x - A_x}{A_w}, \quad t_y = \frac{G_y - A_y}{A_h} \\
  t_w = \text{log}(\frac{G_w}{A_w}), \quad t_h = \text{log}(\frac{G_h}{A_h})
\end{aligned}
$$
</div>

最终的优化目标为：

$$
\hat{W}_* = \text{argmin}_{W_*}\sum_i^N | t_*^i - W_*^T\phi(A) | + \lambda |W_*|
$$

在测试时将预测结果变换回检测框时，需要利用上述公式的逆。假设预测出的偏移为$d_*$,预测检测框的位置为$p_*$,$*\in\{x,y,w,h\}$，则变换函数为：

<div>
$$
\begin{aligned}
  &p_x = d_x\times A_w + A_x \\
  &p_y = d_y\times A_y + A_y \\
  &p_w = e^{A_w}\times t_w \\
  &p_h = e^{A_h}\times t_h
\end{aligned}
$$
</div>

在实际应用过程中，作者发现当Anchor与GroundTruth距离很远时，这种变换将失去意义，因此对靠近一个GroundTruth的框学习，靠近的定义是Anchor与GroundTruth的IOU大于0.6。

在FasterRCNN中该回归使用一层1x1卷积层实现的,其中每个位置处的输出为36个也即每个anchor都有4个偏移。

~~~yaml
layer {
  name: "rpn_bbox_pred"
  type: "Convolution"
  bottom: "rpn/output"
  top: "rpn_bbox_pred"
  param { lr_mult: 1.0 }
  param { lr_mult: 2.0 }
  convolution_param {
    num_output: 36   # 4 * 9(anchors)
    kernel_size: 1 pad: 0 stride: 1
    weight_filler { type: "gaussian" std: 0.01 }
    bias_filler { type: "constant" value: 0 }
  }
}
~~~

## Proposal Layer

RPN最终的输出为
1. 大小为$H\times W\times 2k$的positive/negative softmax分类特征矩阵
2. 大小为$H\times W\times 4k$的bounding box 坐标回归矩阵。

Proposal层的作用就是根据2得到更精确的Positive region，送入ROI Pooling Layer中。

该层的定义为

~~~yaml
layer {
  name: 'proposal'
  type: 'Python'
  bottom: 'rpn_cls_prob_reshape'
  bottom: 'rpn_bbox_pred'
  bottom: 'im_info'
  top: 'rpn_rois'
  python_param {
    module: 'rpn.proposal_layer'
    layer: 'ProposalLayer'
    param_str: "'feat_stride': 16"
  }
}
~~~

Proposal层中rpn_cls_prob_reshape为softmax分类特征矩阵， rpn_bbox_pred为bounding box 坐标回归矩阵，im_info为输入图像的大小和缩放信息。这里的缩放信息是指，输入图片后首先将图片缩放到一个固定的尺寸后再输入到网络，这缩放的比例即为im_scales。而param_str中的feat_stride是指特征图经过4次Pooling，共缩放了16倍，用于计算anchor偏移量。



~~~python
blobs['im_info'] = np.array(
    [[im_blob.shape[2], im_blob.shape[3], im_scales[0]]],
    dtype=np.float32)
~~~

Proposal层实现的具体步骤为：

1. 根据RPN预测的偏移和positive boundingbox生成proposals

~~~python
height, width = scores.shape[-2:]

if DEBUG:
    print 'score map size: {}'.format(scores.shape)

# 根据feat_stride和当前特征图的大小计算原图大小
shift_x = np.arange(0, width) * self._feat_stride
shift_y = np.arange(0, height) * self._feat_stride
shift_x, shift_y = np.meshgrid(shift_x, shift_y)
shifts = np.vstack((shift_x.ravel(), shift_y.ravel(),
                    shift_x.ravel(), shift_y.ravel())).transpose()

# 生成所有像素点处的anchor
A = self._num_anchors
K = shifts.shape[0]
anchors = self._anchors.reshape((1, A, 4)) + \
          shifts.reshape((1, K, 4)).transpose((1, 0, 2))
anchors = anchors.reshape((K * A, 4))

# 将预测得到的bbox transformation转换为与anchor同样的大小
#
# bbox deltas will be (1, 4 * A, H, W) format
# transpose to (1, H, W, 4 * A)
# reshape to (1 * H * W * A, 4) where rows are ordered by (h, w, a)
# in slowest to fastest order
bbox_deltas = bbox_deltas.transpose((0, 2, 3, 1)).reshape((-1, 4))

# 对score做同样的操作
#
# scores are (1, A, H, W) format
# transpose to (1, H, W, A)
# reshape to (1 * H * W * A, 1) where rows are ordered by (h, w, a)
scores = scores.transpose((0, 2, 3, 1)).reshape((-1, 1))

# 根据bbox transformation将anchor转换为proposal
proposals = bbox_transform_inv(anchors, bbox_deltas)
~~~

2. 处理超出图像边界部分的bbox，将图像边界作为超出边界的bbox的边界。

~~~python
def clip_boxes(boxes, im_shape):
    """
    Clip boxes to image boundaries.
    """

    # x1 >= 0
    boxes[:, 0::4] = np.maximum(np.minimum(boxes[:, 0::4], im_shape[1] - 1), 0)
    # y1 >= 0
    boxes[:, 1::4] = np.maximum(np.minimum(boxes[:, 1::4], im_shape[0] - 1), 0)
    # x2 < im_shape[1]
    boxes[:, 2::4] = np.maximum(np.minimum(boxes[:, 2::4], im_shape[1] - 1), 0)
    # y2 < im_shape[0]
    boxes[:, 3::4] = np.maximum(np.minimum(boxes[:, 3::4], im_shape[0] - 1), 0)
    return boxes

proposals = clip_boxes(proposals, im_info[:2])
~~~


3. 去除小于阈值的bbox

~~~python
keep = _filter_boxes(proposals, min_size * im_info[2])
        proposals = proposals[keep, :]
        scores = scores[keep]
~~~

4. 将所有的(proposal, score)对根据score的值进行由高到低排序
5. 取前pre_nms_topN(6000)个值

~~~python
order = scores.ravel().argsort()[::-1]
if pre_nms_topN > 0:
    order = order[:pre_nms_topN]
proposals = proposals[order, :]
scores = scores[order]
~~~

6. 对剩余positive proposals进行NMS，threshold = 0.7
7. 取NMS后的前post_nms_topN(300)个
8. 返回剩余的proposal

~~~python
keep = nms(np.hstack((proposals, scores)), nms_thresh)
if post_nms_topN > 0:
    keep = keep[:post_nms_topN]
proposals = proposals[keep, :]
scores = scores[keep]
~~~

# RoI Pooling

在经过bbox transformation之后，生成的每个bbox都是不同的大小尺寸都不同的，为了保证输入输出尺寸固定且不丢失原始图像的结构和形状，因此采用RoI Pooling的方法。

## RoI Pooing原理

~~~yaml
layer {
  name: "roi_pool_conv5"
  type: "ROIPooling"
  bottom: "conv5"
  bottom: "rois"
  top: "roi_pool_conv5"
  roi_pooling_param {
    pooled_w: 6
    pooled_h: 6
    spatial_scale: 0.0625 # 1/16
  }
}
~~~

RoI Pooling是将每个生成的Proposal都通过pooling的方式变为$\text{pooled}_w\times\text{pooled}_h$的大小，具体步骤为：

1. 由于Proposal层输出的Proposal坐标为在原图的左边， 因此首先利用spatial_scale将Proposal变换到特征图上。
2. 将每个特征图上的Proposal划分成$\text{pooled}_w\times\text{pooled}_h$的网格。
3. 对每个网格进行maxpooling

# Classification

最后根据RoI Pooling层生成的特征使用全连接层对Proposal进行bounding box regression再次获取更高精度的rect box,使用softmax对proposal进行分类。

# BBox Prediction

最终的BoundBox的输出是在每一个PooledFeature上回归得到每一个类别的检测框，对于Pascal VOC数据集，共有21类，因此最终的输出为$4\times 21=84$

~~~yaml
layer {
  name: "bbox_pred"
  type: "InnerProduct"
  bottom: "fc7"
  top: "bbox_pred"
  param {
    lr_mult: 1
  }
  param {
    lr_mult: 2
  }
  inner_product_param {
    num_output: 84
    weight_filler {
      type: "gaussian"
      std: 0.001
    }
    bias_filler {
      type: "constant"
      value: 0
    }
  }
}
~~~

**class-agnostic与class-specific**

前者是指不为每一个类别都预测一个偏移框，仅预测前景和背景，后续通过分类网络得到所有类别的检测结果；后者是指Faster-RCNN采用的方式，为每一个类别都预测一个偏移框。

# Training

训练的过程分为4个步骤：

1. 根据在imagenet上的pretrain训练RPN网络
2. 利用训练好的RPN得到proposal，训练backbone
3. 利用backbone再次训练RPN
4. 利用再次训练backbone

Faster-RCNN的多任务损失函数为：

$$
L(\{p_i\},\{t_i\}) = \frac{1}{N_{cls}}\sum_iL_{cls}(p_i, p_i^*) + \lambda\frac{1}{N_{reg}}\sum_ip_i^*L_{reg}(t_i, t_i^*)
$$

其中，i为anchor的index，$p_i$为anchor中是否包含物体的概率，$p_i^*$为ground truth，当为物体时为1，t_i为预测的bbox的偏移，$t_i^*$为正例的ground truth

## RPNLoss

RPNLoss中的输入是有效的Anhcor，所谓有效的Anchor是指在图像内的anchor，里面包含了正例（<=128）负例（>=128）以及不计算Loss的Anchor(label=-1)

## Proposal Net Loss

在训练过程中，Proposal层最终产生2000个Proposal，输入到ProposalTarget中，由该层采样128个Proposal正负例比例为1:3，将这个128个输入到ROIPooling层中得到特征，对然后输入到FC中计算pred_cla和pred_loc，二者均为128个值，然后用预测值与Proposal生成的Target求差计算Loss

