from __future__ import print_function, division
import os
import torch
import pandas as pd
from skimage import io, transform
import numpy as np
import matplotlib.pyplot as plt
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms, utils

from torch.nn import functional as F
from torch.autograd import Variable
from torch import optim
import torch.nn as nn


class RNN(nn.Module):
    def __init__(self, input_size, hidden_size, output_size):
        super(RNN, self).__init__()

        self.hidden_size = hidden_size
        self.i2h = nn.Linear(input_size + hidden_size, hidden_size)
        self.i2o = nn.Linear(input_size + hidden_size, output_size)
        self.softmax = nn.LogSoftmax(dim=1)

    def step(self, inp, hidden=None):
        combined = torch.cat((inp, hidden), 1)
        hidden = self.i2h(combined)
        output = self.i2o(combined)
        output = self.softmax(output)
        return output, hidden

    def forward(self, inputs, hidden):
        steps = len(inputs)
        outputs = Variable(torch.zeros(steps, 1, 1))
        for i in range(steps):
            output, hidden = self.step(inputs[i], hidden)
            outputs[i] = output
        return outputs, hidden

    def init_hidden(self):
        # TODO gauss init
        return torch.zeros(1, self.hidden_size)


class SimpleLSTM(nn.Module):
    def __init__(self, input_size, hidden_size):
        super(SimpleLSTM, self).__init__()
        self.input_size = input_size
        self.hidden_size = hidden_size

        self.rnn = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=1,
            batch_first=True,
        )
        self.softmax = nn.Softmax()
        self.linear = nn.Linear(self.hidden_size, 3)

    def forward(self, x):
        out, (h_n, h_c) = self.rnn(x, None)
        inp = out[:, -1, :]  # Return output at last time-step
        soft = self.linear(inp)
        out = self.softmax(soft)
        return out

class LSTM2(nn.Module):
    def __init__(self, input_dims, sequence_length, cell_size, output_features=3):
        super(LSTM2, self).__init__()
        self.input_dims = input_dims
        self.sequence_length = sequence_length
        self.cell_size = cell_size
        self.lstm = nn.LSTMCell(input_dims, cell_size)
        self.mlp = nn.Sequential(
            nn.Linear(cell_size, cell_size),
            nn.ReLU(),
            nn.Linear(cell_size, cell_size)
        )
        self.to_output = nn.Linear(cell_size, output_features)

    def forward(self, input):

        h_t, c_t = self.init_hidden(input.size(0))

        outputs = torch.zeroes
        print(input.size())
        print(input[0])
        print(input[1])

        for input_seq in input:
            for frame in input_seq:
                h_t, c_t = self.lstm(frame, (h_t, c_t))
                h_t = self.mlp(h_t)
                # outputs.append(self.to_output(h_t))

        return self.to_output(h_t)  # torch.cat(outputs, dim=1)

    def init_hidden(self, batch_size):
        hidden = Variable(next(self.parameters()).data.new(batch_size, self.cell_size), requires_grad=False)
        cell = Variable(next(self.parameters()).data.new(batch_size, self.cell_size), requires_grad=False)
        return hidden.zero_(), cell.zero_()

class LSTM(nn.Module):

    def __init__(self, input_dim, hidden_dim, batch_size=1, output_dim=3,
                 num_layers=1):
        super(LSTM, self).__init__()
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.batch_size = batch_size
        self.num_layers = num_layers

        # Define the LSTM layer
        self.lstm = nn.LSTM(self.input_dim, self.hidden_dim)

        # Define the output layer
        self.linear = nn.Linear(self.hidden_dim, output_dim)

    def init_hidden(self):
        # This is what we'll initialise our hidden state as
        return (torch.zeros(self.num_layers, self.batch_size, self.hidden_dim),
                torch.zeros(self.num_layers, self.batch_size, self.hidden_dim))

    def forward(self, inputs):
        # Forward pass through LSTM layer
        # shape of lstm_out: [input_size, batch_size, hidden_dim]
        # shape of self.hidden: (a, b), where a and b both
        # have shape (num_layers, batch_size, hidden_dim).
        lstm_out, hidden = self.lstm(inputs.view(len(inputs), self.batch_size, -1))

        # Only take the output from the final timetep
        # Can pass on the entirety of lstm_out to the next layer if it is a seq2seq prediction
        y_pred = lstm_out[-1].view(self.batch_size, -1)
        return y_pred.view(-1)
