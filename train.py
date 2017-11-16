import os
import sys
import tensorflow as tf
import numpy as np
from helpers import import_labeled_csv_data
from neural_network import rank1_ff_nn


def train(train_set, validation_set, nn_layer_sizes, lr, random_seed, nb_epochs, 
          mini_batch_size, log_name, print_log=False):

    # Initialization.
    tf.reset_default_graph()
    np.random.seed(random_seed)

    # Build the computational graph of a feed-forward NN.
    nn = rank1_ff_nn(train_set.nb_features, nn_layer_sizes, train_set.nb_labels,
                     random_seed)

    # Build the training op.
    with tf.name_scope('training'):
        train_step = tf.train.AdamOptimizer(lr).minimize(nn.loss)

    # Print neural network configuration.
    net_config = str(nn_layer_sizes)[1:-1].replace(" ", "")
    hyp_param_settings = net_config + ",lr_%.5E" % (lr) 

    # Collect all summary ops in one op.
    summary = tf.summary.merge_all()

    # Build the validation set dictionary.
    val_feed_dict = { nn.inputs : validation_set.features,
                      nn.labels : validation_set.labels}

    # Run session through the computational graph.
    with tf.Session() as sess:

        # Init.
        init = tf.global_variables_initializer()
        sess.run(init)
        saver = tf.train.Saver()
        writer = tf.summary.FileWriter(hyp_param_settings, graph=sess.graph)

        with open(log_name, "a") as log_file:

            log_file.write(hyp_param_settings + '\n')
    
        # Perform training cycles.
        for epoch in range(nb_epochs):

            # Compute how many minibatches to run through.
            nb_mini_batches = int(train_set.nb_samples/mini_batch_size)

            # Do random shuffling of the indices of training samples.
            shuffled_indices = np.random.permutation(train_set.nb_samples)

            # Running through individual minibatches and doing backprop.
            for i in range(nb_mini_batches):

                mini_batch_indices = shuffled_indices[i:i + mini_batch_size]

                train_feed_dict = { nn.inputs : train_set.features[mini_batch_indices, :],
                                    nn.labels: train_set.labels[mini_batch_indices, :]
                                   }

                # Run training step (which includes backpropagation).
                sess.run([train_step], feed_dict=train_feed_dict)

            # Writing results on validation set to disk.
            validation_summary = sess.run(summary, feed_dict = val_feed_dict)
            writer.add_summary(validation_summary, epoch)

            # Printing accuracies at different levels to see training of NN.
            train_results = sess.run([nn.loss, nn.acc_2pc, nn.acc_1pc], feed_dict=train_feed_dict)
            val_results = sess.run([nn.loss, nn.acc_2pc, nn.acc_1pc], feed_dict=val_feed_dict)
            
            with open(log_name, "a") as log_file:
                log_file.write('Epoch: %i, train loss/acc2pc/acc1pc: %s, validation loss/acc2pc/acc1pc: %s \n'
                                % (epoch, train_results, val_results))
            
            if print_log == True:
                print('Epoch: %i, train loss/acc2pc/acc1pc: %s, validation loss/acc2pc/acc1pc: %s'
                        % (epoch, train_results, val_results))

            # Save checkpoint files for reuse later.
            saver.save(sess, save_path=hyp_param_settings + '/', global_step=epoch)

            # Stop performing training cycles if network performs well on validation set.
            if val_results[2] > 0.99:

                break

        # Saving final model.
        save_path = saver.save(sess, hyp_param_settings + '/' + 'final_model')
    
