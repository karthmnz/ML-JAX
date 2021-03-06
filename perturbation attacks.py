import array
import gzip
import itertools
import numpy
import numpy.random as npr
import os
import struct
import time 
from os import path
import urllib.request

import jax.numpy as np
from jax.api import jit, grad
from jax.config import config
from jax.scipy.special import logsumexp
from jax import random

"""The following cell contains boilerplate code to download and load MNIST data."""

_DATA = "/tmp/"

def _download(url, filename):
  """Download a url to a file in the JAX data temp directory."""
  if not path.exists(_DATA):
    os.makedirs(_DATA)
  out_file = path.join(_DATA, filename)
  if not path.isfile(out_file):
    urllib.request.urlretrieve(url, out_file)
    print("downloaded {} to {}".format(url, _DATA))


def _partial_flatten(x):
  """Flatten all but the first dimension of an ndarray."""
  return numpy.reshape(x, (x.shape[0], -1))


def _one_hot(x, k, dtype=numpy.float32):
  """Create a one-hot encoding of x of size k."""
  return numpy.array(x[:, None] == numpy.arange(k), dtype)


def mnist_raw():
  """Download and parse the raw MNIST dataset."""
  # CVDF mirror of http://yann.lecun.com/exdb/mnist/
  base_url = "https://storage.googleapis.com/cvdf-datasets/mnist/"

  def parse_labels(filename):
    with gzip.open(filename, "rb") as fh:
      _ = struct.unpack(">II", fh.read(8))
      return numpy.array(array.array("B", fh.read()), dtype=numpy.uint8)

  def parse_images(filename):
    with gzip.open(filename, "rb") as fh:
      _, num_data, rows, cols = struct.unpack(">IIII", fh.read(16))
      return numpy.array(array.array("B", fh.read()),
                      dtype=numpy.uint8).reshape(num_data, rows, cols)

  for filename in ["train-images-idx3-ubyte.gz", "train-labels-idx1-ubyte.gz",
                   "t10k-images-idx3-ubyte.gz", "t10k-labels-idx1-ubyte.gz"]:
    _download(base_url + filename, filename)

  train_images = parse_images(path.join(_DATA, "train-images-idx3-ubyte.gz"))
  train_labels = parse_labels(path.join(_DATA, "train-labels-idx1-ubyte.gz"))
  test_images = parse_images(path.join(_DATA, "t10k-images-idx3-ubyte.gz"))
  test_labels = parse_labels(path.join(_DATA, "t10k-labels-idx1-ubyte.gz"))

  return train_images, train_labels, test_images, test_labels


def mnist(create_outliers=False):
  """Download, parse and process MNIST data to unit scale and one-hot labels."""
  train_images, train_labels, test_images, test_labels = mnist_raw()

  train_images = _partial_flatten(train_images) / numpy.float32(255.)
  test_images = _partial_flatten(test_images) / numpy.float32(255.)
  train_labels = _one_hot(train_labels, 10)
  test_labels = _one_hot(test_labels, 10)

  if create_outliers:
    mum_outliers = 30000
    perm = numpy.random.RandomState(0).permutation(mum_outliers)
    train_images[:mum_outliers] = train_images[:mum_outliers][perm]

  return train_images, train_labels, test_images, test_labels

def shape_as_image(images, labels, dummy_dim=False):
  target_shape = (-1, 1, 28, 28, 1) if dummy_dim else (-1, 28, 28, 1)
  return np.reshape(images, target_shape), labels

train_images, train_labels, test_images, test_labels = mnist(create_outliers=False)
num_train = train_images.shape[0]

"""# **Problem 1**

This function computes the output of a fully-connected neural network (i.e., multilayer perceptron) by iterating over all of its layers and:

1. taking the `activations` of the previous layer (or the input itself for the first hidden layer) to compute the `outputs` of a linear classifier. Recall the lectures: `outputs` is what we wrote $z=w\cdot x + b$ where $x$ is the input to the linear classifier. 
2. applying a non-linear activation. Here we will use $tanh$.

Complete the following cell to compute `outputs` and `activations`.
"""

def predict(params, inputs):
  activations = inputs
  
  for w, b in params[:-1]:
    outputs = np.dot(activations, w) + b
    activations = np.tanh(outputs)

  final_w, final_b = params[-1]
  logits = np.dot(activations, final_w) + final_b
  pred = logits - logsumexp(logits, axis=1, keepdims=True)
  return pred

"""The following cell computes the loss of our model. Here we are using cross-entropy combined with a softmax but the implementation uses the `LogSumExp` trick for numerical stability. This is why our previous function `predict` returns the logits to which we substract the `logsumexp` of logits. We discussed this in class but you can read more about it [here](https://blog.feedly.com/tricks-of-the-trade-logsumexp/).

Complete the return line. Recall that the loss is defined as :
$$ l(X, Y) = -\frac{1}{n} \sum_{i\in 1..n}  \sum_{j\in 1.. K}y_j^{(i)} \log(f_j(x^{(i)})) = -\frac{1}{n} \sum_{i\in 1..n}  \sum_{j\in 1.. K}y_j^{(i)} \log\left(\frac{z_j^{(i)}}{\sum_{k\in 1..K}z_k^{(i)}}\right) $$
where $X$ is a matrix containing a batch of $n$ training inputs, and $Y$ a matrix containing a batch of one-hot encoded labels defined over $K$ labels. Here $z_j^{(i)}$ is the logits (i.e., input to the softmax) of the model on the example $i$ of our batch of training examples $X$.
"""

def loss(params, inputs, targets):
  
  preds = predict(params, inputs)
  temp = targets * preds
  sum_ = np.sum(temp, axis=1)
  return -np.sum(sum_)/inputs.shape[0]

# def loss_in(loss, inputs):
#   return inputs

"""The following cell defines the accuracy of our model and how to initialize its parameters."""

def accuracy(params, inputs, targets):
  target_class = np.argmax(targets, axis=1)
  predicted_class = np.argmax(predict(params, inputs), axis=1)
  return np.mean(predicted_class == target_class)

def init_random_params(layer_sizes, rng=npr.RandomState(0)):
  scale = 0.1
  return [(scale * rng.randn(m, n), scale * rng.randn(n))
          for m, n, in zip(layer_sizes[:-1], layer_sizes[1:])]

"""The following line defines our architecture with the number of neurons contained in each fully-connected layer (the first layer has 784 neurons because MNIST images are 28*28=784 pixels and the last layer has 10 neurons because MNIST has 10 classes)"""

layer_sizes = [784, 1024, 128, 10]

"""The following cell creates a Python generator for our dataset. It outputs one batch of $n$ training examples at a time."""

batch_size = 128
num_complete_batches, leftover = divmod(num_train, batch_size)
num_batches = num_complete_batches + bool(leftover)

def data_stream():
  rng = npr.RandomState(0)
  while True:
    perm = rng.permutation(num_train)
    for i in range(num_batches):
      batch_idx = perm[i * batch_size:(i + 1) * batch_size]
      yield train_images[batch_idx], train_labels[batch_idx]
batches = data_stream()
print(batches)

"""We are now ready to define our optimizer. Here we use mini-batch stochastic gradient descent. Complete `<w UPDATE RULE>` and `<b UPDATE RULE>` using the update rule we saw in class. Recall that `dw` is the partial derivative of the `loss` with respect to `w` and `learning_rate` is the learning rate of gradient descent."""

learning_rate = 0.07

@jit
def update(params, inputs, targets):
  grads = grad(loss)(params, inputs, targets)
  return [(w - learning_rate * dw, b - learning_rate * db) for (w, b),(dw, db) in zip(params, grads)]

"""This is now the proper training loop for our fully-connected neural network."""

num_epochs = 10
params = init_random_params(layer_sizes)
for epoch in range(num_epochs):
  start_time = time.time()
  for _ in range(num_batches):
    inputs, targets = next(batches)
    params = update(params, inputs, targets)
    
  epoch_time = time.time() - start_time

  train_acc = accuracy(params, train_images, train_labels)
  test_acc = accuracy(params, test_images, test_labels)
  print("Epoch {} in {:0.2f} sec".format(epoch, epoch_time))
  print("Training set accuracy {}".format(train_acc))
  print("Test set accuracy {}".format(test_acc))

# print(test_images)

# print(test_labels[4])

"""**SECTION 1**"""

def image_getter(k):
  for x, y in zip(test_images, test_labels):
    for i in range(10000):
      if test_labels[i][k]==1.0:
        print("Image At Index: {}".format(i))
        x, y = test_images[i], test_labels[i]
        return x, y

x, y = image_getter(7)

import matplotlib.pyplot as plt
x = x.reshape(28,28)
plt.imshow(x)

x = x.reshape(1,-1)
predicted_class_ = np.argmax(predict(params, x), axis=1)
print(predicted_class_)

def create_adversary(x, y, hyper):
  gradient = grad(loss, 1)(params, x , y)
  signed_gradient = numpy.sign(numpy.array(gradient))
  x = x + hyper * signed_gradient
  return x

adv = create_adversary(x, y, 0.3)
predicted_class = np.argmax(predict(params, adv), axis=1)
fig, (ax1, ax2) = plt.subplots(1,2,figsize=(15,15))
ax1.imshow(adv.reshape(28,28))
ax1.set_title("Attacked Image...predicted class: {}".format(predicted_class))
ax2.imshow(x.reshape(28,28))
ax2.set_title("Original Image..predicted class: {}".format(predicted_class_))

print("Prediction vector on original_image: {}\n".format(predict(params, x)))
print("Prediction vector on perturbed_image: {}\n".format(predict(params, adv)))

"""**SECTION 2**"""

hyper_list = [i for i in numpy.arange(0,0.5,0.001)]
print(hyper_list) 

idx = numpy.random.choice(np.arange(len(test_images)), 1000, replace=False)
image = test_images[idx]
label = test_labels[idx]

original_acc = []
attack_acc = []
for hyper in range(len(hyper_list)):
  hyper_ = hyper_list[hyper]
  adv = create_adversary(image, label, hyper_)
  acc = accuracy(params,image,label)
  acc_ = accuracy(params,adv,label)
  original_acc.append(acc)
  attack_acc.append(acc_)

plt.plot(hyper_list, attack_acc)
plt.xlabel("Epsilon")
plt.ylabel("Accuracy")
plt.title("Accuracy as a function of epsilon")

"""**SECTION 3**"""

def mod_create_adversary(x, y, hyper, k):
  for i in range(k):
    gradient = grad(loss, 1)(params, x , y)
    signed_gradient = numpy.sign(numpy.array(gradient))
    x = x + hyper * signed_gradient
  return x

adv = mod_create_adversary(x, y, 0.03, 5)
predicted_class = np.argmax(predict(params, adv), axis=1)
fig, (ax1, ax2) = plt.subplots(1,2,figsize=(15,15))
ax1.imshow(adv.reshape(28,28))
ax1.set_title("Attacked Image...predicted class: {}".format(predicted_class))
ax2.imshow(x.reshape(28,28))
ax2.set_title("Original Image..predicted class: {}".format(predicted_class_))

print("Prediction vector on original_image: {}\n".format(predict(params, x)))
print("Prediction vector on perturbed_image: {}\n".format(predict(params, adv)))

"""**SECTION 4**"""

hyper_list2 = [i for i in numpy.arange(0,0.5,0.001)]
print(hyper_list2)

# hyper_list = [0.001, 0.1, 0.2, 0.3, 0.4, 0.5] 

idx = numpy.random.choice(np.arange(len(test_images)), 1000, replace=False)
image = test_images[idx]
label = test_labels[idx]

original_acc2 = []
attack_acc2 = []
for hyper in range(len(hyper_list)):
  hyper_ = hyper_list[hyper]
  adv = mod_create_adversary(image, label, hyper_, 5)
  acc = accuracy(params,image,label)
  acc_ = accuracy(params,adv,label)
  original_acc2.append(acc)
  attack_acc2.append(acc_)

plt.plot(hyper_list, attack_acc2)
plt.xlabel("Epsilon")
plt.ylabel("Accuracy")
plt.title("Accuracy as a function of epsilon")

fig, (ax1, ax2) = plt.subplots(1,2,figsize=(12,6))

ax1.plot(hyper_list, attack_acc)
ax1.set_title("Accuracy as a function of epsilon")


ax2.plot(hyper_list, attack_acc2)
ax2.set_title("Accuracy as a function of epsilon - Iterated perturbation")

