# **Karthik Mohan**               **1006179145**                   **mohanka2**

X_data in plots: x from dataset
PCA x_data: PCA of x

**Data Exploration**
"""

import sklearn
from sklearn.datasets import load_breast_cancer
from sklearn.preprocessing import StandardScaler
from copy import deepcopy
import pandas as pd
import numpy as np
from numpy.linalg import svd

data = load_breast_cancer()
print(data)

print(data['feature_names'])
print(data['target_names'])

df = pd.DataFrame(data= np.c_[data.data, data.target])

print(df)

df.describe()

"""**PCA**"""

datas = load_breast_cancer()
x, y = datas.data, datas.target

mean = x.mean(axis=0)
std = x.std(axis=0)
x = (x-mean)/std #mean normalisation and feature scaling

def pca(x, k):
  covar = np.cov(x.T) #covariance
  u,s,v = svd(covar) #svd
  eigenval = s**2

  args = (-eigenval).argsort()
  eigenval = eigenval[args]
  u = u[:, args]
  u_ = u[:, :k]

  return u_

u_ = pca(x, 2)
projection = np.dot(x, u_)
print(projection.shape)

print(projection)

import matplotlib.pyplot as plt
fig, (ax1, ax2) = plt.subplots(1,2,figsize=(30,10))
label_list = [datas.target_names[0] if i==0 else datas.target_names[1] for i in set(y)]
for label in set(y):
    ax1.plot(projection[y==label, 0], projection[y==label, 1], 'o', label = label_list[label])
    ax1.legend(loc='upper right')
    ax1.set_title("X DATA PCA")

label_list = [datas.target_names[0] if i==0 else datas.target_names[1] for i in set(y)]
for label in set(y):
    ax2.plot(x[y==label, 0], x[y==label, 1], 'o', label = label_list[label])
    ax2.legend(loc='upper right')
    ax2.set_title("X DATA")

"""**KNN**"""

no_of_clusters = 2

def knn(x, no_of_clusters):
  no_of_samples, no_of_features = x.shape[0], x.shape[1]
  
  '''random points huerestic'''
  
  centroid = np.random.rand(no_of_clusters,no_of_features)
  # mean = np.mean(centroid, axis = 0)
  # std = np.std(centroid, axis = 0)
  # centroid = (1/std)*(centroid-mean)

  old = np.zeros(centroid.shape)
  new = deepcopy(centroid)

  clusters = np.zeros(no_of_samples)
  distances = np.zeros((no_of_samples,no_of_clusters))

  difference = np.linalg.norm(new - old)

  while difference != 0: # until convergence
      for i in range(no_of_clusters):
          distances[:,i] = np.linalg.norm(x - new[i], axis=1) #for each centroid, measure the distance between other points
      clusters = np.argmin(distances, axis = 1) #assign the minimum distance to the cluster
      
      old = deepcopy(new)

      for i in range(no_of_clusters):
          new[i] = np.mean(x[clusters == i], axis=0)
      difference = np.linalg.norm(new - old)
  return new, clusters

center, cluster = knn(x, no_of_clusters)

plt.figure(figsize=(20,20))
label_list = [datas.target_names[0] if i==0 else datas.target_names[1] for i in set(y)]
print(label_list)
plt.scatter(center[:,0], center[:,1], marker='X', s=500, c='r')

for label in set(y):
    plt.plot(x[y==label, 0], x[y==label, 1], 'o', label = label_list[label])
    plt.legend(loc='upper right')
    plt.title("X_DATA for K value: {}".format(2))

k_list =[i for i in range(2,8,1)]
print(k_list)

for no_Of_Clusters in k_list:
  label_list = [datas.target_names[0] if i==0 else datas.target_names[1] for i in set(y)]
  center, cluster  = knn(x, no_Of_Clusters)
  plt.figure(figsize=(20,10))

  for i in range(no_Of_Clusters):
    plt.scatter(center[:,0], center[:,1], marker='X', s=500, c='r')
  for label in set(y):
    plt.plot(x[y==label, 0], x[y==label, 1], 'o', label = label_list[label])
    plt.legend(loc='upper right')
    plt.title("X_DATA for K value: {}".format(no_Of_Clusters))

for i in range(len(k_list)):
  no_ = k_list[i]
  no_of_samples = x.shape[0]
  center_, cluster_ = knn(x, no_)
  projected_centers = np.dot(center_, u_)
  plt.figure(figsize=(20,10))  
  label_list = [datas.target_names[0] if i==0 else datas.target_names[1] for i in set(y)]

  for i in range(2):
    plt.scatter(projected_centers[:,0], projected_centers[:,1], marker='X', s=500, c='r')
  
  for label in set(y):
    plt.plot(projection[y==label, 0], projection[y==label, 1], 'o', label = label_list[label])
    plt.legend(loc='upper right')
    plt.title("X_DATA PCA for K value: {}".format(no_))

"""**Linear Classification**"""

from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report

x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.2, random_state=42)

W = np.dot(np.linalg.inv(np.dot(x_train.T, x_train)), np.dot(x_train.T, y_train))
print(W)

x_train_z = np.dot(x_train, W)
print(x_train_z.shape)
def sigmoid_activation(x):
  k = 1/(1 + np.exp(-x))
  return k
x_train_pred = sigmoid_activation(x_train_z)
x_train_pred[x_train_pred >= 0.5] = int(1)
x_train_pred[x_train_pred < 0.5] = int(0)

train_score = accuracy_score(x_train_pred, y_train)
x_test_pred = sigmoid_activation(np.dot(x_test, W))
x_test_pred[x_test_pred >= 0.5] = int(1)
x_test_pred[x_test_pred < 0.5] = int(0)
test_score = accuracy_score(x_test_pred, y_test)

print("\n*********************************\n")
print("Train Score: {}".format(train_score))
print("Test Score: {}".format(test_score))

conf_train = confusion_matrix(y_train, x_train_pred)
conf_test = confusion_matrix(y_test, x_test_pred)
print("\n*********************************\n")
print("Train confusion matrix: \n\n{}".format(conf_train))
print("\nTest confusion matrix: \n\n{}".format(conf_test))

clf_train = classification_report(y_train, x_train_pred)
clf_test = classification_report(y_test, x_test_pred)

print("\n*********************************\n")
print("Train report: \n\t{}".format(clf_train))
print("Test report: \n\t{}".format(clf_test))

x_test_pred = x_test_pred.astype(int)
print(x_test_pred-y_test)

plt.figure(figsize=(20,10))  
projected_test_x = np.dot(x_test, u_)
# projected_test_
label_list_ = ['predicted'+' ' + datas.target_names[0], 'predicted'+' ' + datas.target_names[1] ]
label_list = [datas.target_names[0] if i==0 else datas.target_names[1] for i in set(y)]
colors_list = ['red','yellow']
colors_list_ = ['grey','black']
# colors_list = ['red','green']              #uncomment to see misclassifications plot
# colors_list_ = ['blue','orange']
for label in set(y_test):
  plt.plot(projected_test_x[y_test==label, 0], projected_test_x[y_test==label, 1], 'o', label = label_list[label],c=colors_list[label])
  plt.legend(loc='upper right')

for label in set(x_test_pred):
  plt.plot(projected_test_x[x_test_pred==label, 0], projected_test_x[x_test_pred==label, 1], 'x', label = label_list_[label], markersize=12, c=colors_list_[label])
  plt.legend(loc='upper right')
plt.title("PCA: X_TEST_DATA")

plt.figure(figsize=(20,10))  
pred_whole_x = sigmoid_activation(np.dot(x, W))
pred_whole_x[pred_whole_x >= 0.5] = int(1)
pred_whole_x[pred_whole_x < 0.5] = int(0)
pred_whole_x = pred_whole_x.astype(int)
colors_list = ['red','yellow']
colors_list_ = ['grey','black']
# colors_list = ['red','green']                         #uncomment to see misclassifications plot
# colors_list_ = ['blue','orange']
label_list_ = ['predicted'+' ' + datas.target_names[0], 'predicted'+' ' + datas.target_names[1]]
label_list = [datas.target_names[0] if i==0 else datas.target_names[1] for i in set(y)]
for label in set(y_test):
  plt.plot(projection[y==label, 0], projection[y==label, 1], 'o', label = label_list[label],c=colors_list[label])
  plt.legend(loc='upper right')

for label in set(pred_whole_x):
  plt.plot(projection[pred_whole_x==label, 0], projection[pred_whole_x==label, 1], 'x', label = label_list_[label], markersize=12, c=colors_list_[label])
  plt.legend(loc='upper right')
plt.title("PCA: X_DATA")
