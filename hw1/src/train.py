#########################################################
#   FileName:       [ train.py ]                        #
#   PackageName:    [ DNN ]                             #
#   Synopsis:       [ Train DNN model ]                 #
#   Author:         [ MedusaLafayetteDecorusSchiesse ]  #
#########################################################

import sys
import time
import cPickle
import random
import math
import argparse
import signal

import numpy as np
import theano
import theano.tensor as T

from nn.dnn import MLP

parser = argparse.ArgumentParser(prog='train.py', description='Train DNN for Phone Classification.')
parser.add_argument('--input-dim', type=int, required=True, metavar='<nIn>',
					help='input dimension of network')
parser.add_argument('--output-dim', type=int, required=True, metavar='<nOut>',
					help='output dimension of network')
parser.add_argument('--hidden-layers', type=int, required=True, metavar='<nLayers>',
					help='number of hidden layers')
parser.add_argument('--neurons-per-layer', type=int, required=True, metavar='<nNeurons>',
					help='number of neurons in a hidden layer')
parser.add_argument('--max-epochs', type=int, required=True, metavar='<nEpochs>',
					help='number of maximum epochs')
parser.add_argument('--batch-size', type=int, default=1, metavar='<size>',
					help='size of minibatch')
parser.add_argument('--learning-rate', type=float, default=0.0001, metavar='<rate>',
					help='learning rate of gradient descent')
parser.add_argument('--learning-rate-decay', type=float, default=1., metavar='<decay>',
					help='learning rate decay')
parser.add_argument('--momentum', type=float, default=0., metavar='<momentum>',
					help='momentum in gradient descent')
parser.add_argument('--l1-reg', type=float, default=0.,
					help='L1 regularization')
parser.add_argument('--l2-reg', type=float, default=0.,
					help='L2 regularization')
parser.add_argument('train_in', type=str, metavar='train-in',
					help='training data file name')
parser.add_argument('dev_in', type=str, metavar='dev-in',
					help='development data file name')
parser.add_argument('model_out', type=str, metavar='model-out',
					help='the output file name you want for the output model')
args = parser.parse_args()

INPUT_DIM = args.input_dim
OUTPUT_DIM = args.output_dim
HIDDEN_LAYERS = args.hidden_layers
NEURONS_PER_LAYER = args.neurons_per_layer
EPOCHS = args.max_epochs
BATCH_SIZE = args.batch_size
LEARNING_RATE = args.learning_rate
LEARNING_RATE_DECAY = args.learning_rate_decay
MOMENTUM = args.momentum
L1_REG = args.l1_reg
L2_REG = args.l2_reg
SQUARE_GRADIENTS = 0

start_time = time.time()

########################
# Function Definitions #
########################

def LoadData(filename, load_type):
    with open(filename,'rb') as f:
        if load_type == 'train_xy':
            data_x, data_y = cPickle.load(f)
            shared_x = data_x
            shared_y = theano.shared(data_y, borrow=True)
            return shared_x, shared_y
        elif load_type == 'dev_xy':
            data_x, data_y = cPickle.load(f)
            shared_x = theano.shared(data_x)
            shared_y = theano.shared(data_y, borrow=True)
            return shared_x, shared_y
        elif load_type == 'train_y':
            data_y = cPickle.load(f)
            shared_y = theano.shared(data_y, borrow=True)
            return shared_y

'''
#momentum
def Update(params, gradients, velocities):
    global MOMENTUM
    global LEARNING_RATE
    global LEARNING_RATE_DECAY
    param_updates = [ (v, v * MOMENTUM - LEARNING_RATE * g) for g, v in zip(gradients, velocities) ]
    for i in range(0, len(gradients)):
        velocities[i] = velocities[i] * MOMENTUM - LEARNING_RATE * gradients[i]
    param_updates.extend([ (p, p + v) for p, v in zip(params, velocities) ])
    LEARNING_RATE *= LEARNING_RATE_DECAY
    return param_updates
'''

#adagrad
def Update(params, gradients, square_gra):
    global LEARNING_RATE
    param_updates = [ (s, s + g*g) for g, s in zip(gradients, square_gra) ]
    for i in range(0, len(gradients)):
        square_gra[i] = square_gra[i] + gradients[i] * gradients[i]
    param_updates.extend([ (p, p - LEARNING_RATE * g /T.sqrt(s) ) for p, s, g in zip(params, square_gra, gradients) ])
    return param_updates

def print_dev_acc():
    print "\n===============dev_acc==============="
    for acc in dev_acc:
        print >> sys.stderr, acc

def interrupt_handler(signal, frame):
    print >> sys.stderr, str(signal)
    print >> sys.stderr, "Total time till last epoch: %f" % (now_time-start_time)
    print_dev_acc()
    sys.exit(0)

##################
#   Load Data    #
##################

# Load Dev data
print("===============================")
print("Loading dev data...")
f_xy = args.dev_in + ".xy"
val_x, val_y = LoadData(f_xy,'dev_xy')
print("Current time: %f" % (time.time()-start_time))

# Load Training data
print("===============================")
print("Loading training data...")
# train_x, train_y = LoadData(args.train_in,'train_xy')
f_y = args.train_in + '.y'
train_y = LoadData(f_y,'train_y')
print("Current time: %f" % (time.time()-start_time))

print >> sys.stderr, "After loading: %f" % (time.time()-start_time)

###############
# Build Model #
###############

# symbolic variables
index = T.lscalar()
x = T.matrix(dtype=theano.config.floatX)
y = T.ivector()

# construct MLP class
classifier = MLP(
        input=x,
        n_in=INPUT_DIM,
        n_hidden=NEURONS_PER_LAYER,
        n_out=OUTPUT_DIM,
        n_layers=HIDDEN_LAYERS
)

# cost + regularization terms; cost is symbolic
cost = (
        classifier.negative_log_likelihood(y) +
        L1_REG * classifier.L1 +
        L2_REG * classifier.L2_sqr
)

# compile "dev model" function
dev_model = theano.function(
        inputs=[index],
        outputs=classifier.errors(y),
        givens={
            x: val_x[ index * BATCH_SIZE : (index + 1) * BATCH_SIZE ].T,
            y: val_y[ index * BATCH_SIZE : (index + 1) * BATCH_SIZE ].T,
        }
)


# gradients
dparams = [ T.grad(cost, param) for param in classifier.params ]

# compile "train model" function
train_model = theano.function(
        #inputs=[index],
        inputs=[x, index],
        outputs=cost,
        updates=Update(classifier.params, dparams, classifier.velo),
        givens={
            #x: train_x[ index * BATCH_SIZE : (index + 1) * BATCH_SIZE ].T,
            y: train_y[ index * BATCH_SIZE : (index + 1) * BATCH_SIZE ].T
        }
)

###############
# Train Model #
###############

print("===============================")
print("            TRAINING           ")
print("===============================")

train_num = int(math.ceil(train_y.shape[0].eval()/BATCH_SIZE))
val_num = int(math.ceil(val_y.shape[0].eval()/BATCH_SIZE))
print >> sys.stderr, "Input dimension: %i" % INPUT_DIM
print >> sys.stderr, "Output dimension: %i" % OUTPUT_DIM
print >> sys.stderr, "# of layers: %i" % HIDDEN_LAYERS
print >> sys.stderr, "# of neurons per layer: %i" % NEURONS_PER_LAYER
print >> sys.stderr, "Max epochs: %i" % EPOCHS
print >> sys.stderr, "Batch size: %i" % BATCH_SIZE
print >> sys.stderr, "Learning rate: %f" % LEARNING_RATE
print >> sys.stderr, "Learning rate decay: %f" % LEARNING_RATE_DECAY
print >> sys.stderr, "Momentum: %f" % MOMENTUM
print >> sys.stderr, "L1 regularization: %f" % L1_REG
print >> sys.stderr, "L2 regularization: %f" % L2_REG
print >> sys.stderr, "iters per epoch: %i" % train_num
print >> sys.stderr, "validation size: %i" % val_y.shape[0].eval()

first = -1.0
second = -1.0
third = -1.0

minibatch_indices = range(0, train_num)
epoch = 0
dev_acc = []
now_time = time.time()

# set keyboard interrupt handler
signal.signal(signal.SIGINT, interrupt_handler)
# set shutdown handler
signal.signal(signal.SIGTERM, interrupt_handler)

while epoch < EPOCHS:
    epoch += 1
    print("===============================")
    print("EPOCH: " + str(epoch))
    random.shuffle(minibatch_indices)
    for minibatch_index in minibatch_indices:
        file_batch = args.train_in + ".x." + str(minibatch_index)
        with open(file_batch, "rb") as f:
            x_in = cPickle.load(f)
        # print("training: " + str(time.time()-start_time))
        batch_cost = train_model(x_in, minibatch_index)
        # print("trained: " + str(time.time()-start_time))
        #print("cost: " + str(batch_cost))
        if math.isnan(batch_cost):
            print >> sys.stderr, "Epoch #%i: nan error!!!" % epoch
            sys.exit()
    val_acc = 1 - np.mean([ dev_model(i) for i in xrange(0, val_num) ])
    if val_acc > first:
        print("!!!!!!!!!!FIRST!!!!!!!!!!")
        third = second
        second = first
        first = val_acc
        classifier.save_model(args.model_out)
    elif val_acc > second:
        print("!!!!!!!!!!SECOND!!!!!!!!!!")
        third = second
        second = val_acc
        classifier.save_model(args.model_out + ".2")
    elif val_acc > third:
        print("!!!!!!!!!!THIRD!!!!!!!!!!")
        third = val_acc
        classifier.save_model(args.model_out + ".3")
    dev_acc.append(val_acc)
    now_time = time.time()
    print("dev accuracy: " + str(dev_acc[-1]))
    print("Current time: " + str(now_time-start_time))
    classifier.save_model("models/temp.mdl")

print("===============================")
print >> sys.stderr, "Total time: %f" % (time.time()-start_time)
print_dev_acc()

print("===============================")
print("Total time: " + str(time.time()-start_time))
print("===============================")
