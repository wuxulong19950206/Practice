import tensorflow as tf
import numpy as np
import os
import time
import datetime
import data_helper
from tensorflow.contrib import learn
from text_cnn import TextCNN

os.environ['CUDA_VISIBLE_DEVICES'] = '0'  # 指定一个GPU
# parameters

# Data loadding  params
tf.flags.DEFINE_string(flag_name='train_data_file', default_value='./data/train_text.txt',
                       docstring='train data')
tf.flags.DEFINE_string(flag_name='train_label_file', default_value='./data/train_label.txt',
                       docstring='train label')

tf.flags.DEFINE_string(flag_name='test_data_file', default_value='./data/test_text.txt',
                       docstring='test data')
tf.flags.DEFINE_string(flag_name='test_label_file', default_value='./data/test_label.txt',
                       docstring='test label')

tf.flags.DEFINE_string(flag_name='embedding_file', default_value='./data/sgns.merge.word',
                       docstring='test label')

# Model hyperparams
tf.flags.DEFINE_integer(flag_name='embedding_dimension', default_value=300, docstring='dimensionality of word')
tf.flags.DEFINE_integer(flag_name='padding_sentence_length', default_value=7, docstring='padding seize of eatch sample')
tf.flags.DEFINE_string(flag_name='filter_size', default_value='3,4,5', docstring='filter size ')
tf.flags.DEFINE_integer(flag_name='num_filters', default_value=128, docstring='deep of filters')
tf.flags.DEFINE_float(flag_name='dropout', default_value=0.5, docstring='Drop out')
tf.flags.DEFINE_float(flag_name='L2_reg_lambda', default_value=0.0, docstring='L2')

# Training params
tf.flags.DEFINE_integer(flag_name='batch_size', default_value=64, docstring='batch size')
tf.flags.DEFINE_float(flag_name='learning_rate', default_value=0.1, docstring='learning rate')

tf.flags.DEFINE_boolean(flag_name='allow_soft_placement', default_value='True',
                        docstring='allow_soft_placement')  # 找不到指定设备时，是否自动分配
tf.flags.DEFINE_boolean(flag_name='log_device_placement', default_value='False',
                        docstring='log_device_placement ')  # 是否打印配置日志

FLAGS = tf.flags.FLAGS
# FLAGS.flag_values_dict()  # 解析参数成字典
FLAGS._parse_flags()

print('\n----------------Parameters--------------')  # 在网络训练之前，先打印出来看看
for attr, value in sorted(FLAGS.__flags.items()):
    print('{}={}'.format(attr.upper(), value))

# Load data and cut
x_train_data, y_train = data_helper.load_data_and_labels(FLAGS.train_data_file, FLAGS.train_label_file)
x_test_data, y_test = data_helper.load_data_and_labels(FLAGS.test_data_file, FLAGS.test_label_file)

# Padding sentence
padded_sentences_train, max_padding_length = data_helper.padding_sentence(
    sentences=x_train_data, padding_sentence_length=FLAGS.padding_sentence_length)
padded_sentences_test, max_padding_length = data_helper.padding_sentence(
    sentences=x_test_data, padding_sentence_length=FLAGS.padding_sentence_length)

x_test, vocabulary_len = data_helper.embedding_sentences(
    embedding_file=FLAGS.embedding_file, padded_sentences=padded_sentences_test,
    embedding_dimension=FLAGS.embedding_dimension)
x_train, vocabulary_len = data_helper.embedding_sentences(
    embedding_file=FLAGS.embedding_file, padded_sentences=padded_sentences_train,
    embedding_dimension=FLAGS.embedding_dimension)


print('--------------------------preProcess finished!-----------------------')
print('--------------------------preProcess finished!-----------------------')
print("vocabulary length={}".format(vocabulary_len))
print("x_train.shape = {}".format(x_train.shape))
print("y_train.shape = {}".format(y_train.shape))
print("x_test.shape = {}".format(x_test.shape))
print("y_test.shape = {}".format(y_test.shape))
print('train/dev split:{:d}/{:d}'.format(len(y_train), len(y_test)))
# print(y_train[:100])
#


with tf.Graph().as_default():
    session_conf = tf.ConfigProto(allow_soft_placement=FLAGS.allow_soft_placement,
                                  log_device_placement=FLAGS.log_device_placement)
    session_conf.gpu_options.per_process_gpu_memory_fraction = 0.6
    session_conf.gpu_options.allow_growth = True
    sess = tf.Session(config=session_conf)
    with sess.as_default():
        cnn = TextCNN(sequence_length=x_train.shape[1],
                      num_classes=3510,
                      embedding_dimension=FLAGS.embedding_dimension,
                      filter_sizes=list(map(int, FLAGS.filter_size.split(','))),
                      num_filters=FLAGS.num_filters,
                      l2_reg_lambda=FLAGS.L2_reg_lambda
                      )
        global_step = tf.Variable(0, trainable=False)
        with tf.device('/gpu:0'):
            train_step = tf.train.GradientDescentOptimizer(
                FLAGS.learning_rate).minimize(loss=cnn.loss, global_step=global_step)
            # train_step = tf.train.AdamOptimizer(1e-3).minimize(loss=cnn.loss, global_step=global_step)
    sess.run(tf.global_variables_initializer())
    last = datetime.datetime.now()
    for i in range(500000):
        x, y = data_helper.gen_batch(x_train, y_train, i, FLAGS.batch_size)
        feed_dic = {cnn.input_x: x, cnn.input_y: y, cnn.dropout_keep_prob: FLAGS.dropout}
        _, loss, acc = sess.run([train_step, cnn.loss, cnn.accuracy], feed_dict=feed_dic)

        if (i % 100) == 0:
            now = datetime.datetime.now()
            print('loss:{},acc:{}---time:{}'.format(loss, acc, now - last))
            last = now
        if (i % 1000 == 0):
            feed_dic = {cnn.input_x: x_test, cnn.input_y: y_test, cnn.dropout_keep_prob: 1.0}
            _, loss, acc = sess.run([train_step, cnn.loss, cnn.accuracy], feed_dict=feed_dic)
            print('-------------loss:{},acc:{}---time:{}--step:{}'.format(loss, acc, now - last, i))