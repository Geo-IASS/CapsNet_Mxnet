from mxnet import nd
from mxnet.gluon import nn,Parameter
# from mxnet import gluon


def squash(vectors):
    s_squared_norm = nd.sum(nd.square(vectors), -1, keepdims=True)
    scale = s_squared_norm / (1 + s_squared_norm) / nd.sqrt(s_squared_norm)
    return scale * vectors

class PrimaryCap(nn.Block):
    def __init__(self,dim_vector,n_channels,kernel_size,padding,strides=(1,1),**kwargs):
        super(PrimaryCap, self).__init__(**kwargs)
        # self.squash = squash()
        self.net = nn.Sequential()
        self.output = []
        self.outputs = []
        self.s_squared_norm = 0
        self.scale = 0
        self.dim_vector = dim_vector
        self.n_channels=n_channels
        # self.dense = nn.Dense(64)
        with self.name_scope():
            self.net.add(nn.Conv2D(channels=dim_vector,kernel_size=kernel_size,strides=strides,padding=padding,activation="relu"))


    def forward(self, x):
        # print('PrimaryCap inputs shape',x.shape)
        outputs = []
        for _ in range(self.n_channels):
            self.output = self.net(x)

            outputs.append(nd.reshape(data=self.output,shape=(-1, self.dim_vector,self.output.shape[2] ** 2)))
            # print(self.output.shape)
            # print(self.outputs[-1].shape)
        
        outputs = nd.concatenate(outputs, axis=2)
        
        # squash
        # print('outputs',self.outputs.shape)
        self.s_squared_norm = nd.sum(nd.square(outputs), -1, keepdims=True)
        self.scale = self.s_squared_norm / (1 + self.s_squared_norm) / nd.sqrt(self.s_squared_norm)

        return self.scale * outputs


class CapsuleLayer(nn.Block):
    def __init__(self,num_capsule,dim_vector, batch_size, num_routing=3,**kwargs):
        super(CapsuleLayer, self).__init__(**kwargs)
        self.num_capsule = num_capsule
        self.dim_vector = dim_vector
        self.batch_size = batch_size
        self.num_routing = num_routing

        self.input_num_capsule = 1152
        self.input_dim_vector = 8

        self.W  = self.params.get(
                'weight',shape=(self.batch_size,self.input_dim_vector, self.dim_vector))
        self.bias = self.params.get('bias', shape=(self.input_num_capsule, self.num_capsule))
        self.Weight = Parameter("Wij", shape=(self.input_num_capsule, self.num_capsule, self.input_dim_vector, self.dim_vector))

    def squash(self,vectors):
        s_squared_norm = nd.sum(nd.square(vectors), -1, keepdims=True)
        scale = s_squared_norm / (1 + s_squared_norm) / nd.sqrt(s_squared_norm)
        return scale * vectors

    def forward(self, x):
        # print('CapsuleLayer inputs shape',x.shape)
        # print('W',self.W.shape)
        # print('bias',self.bias.shape)
        # (2, 8, 1152)
        # inputs.shape=[batch_size, input_dim_vector,input_num_capsule]
        # Expand dims to [batch_size, input_dim_vector, 1, 1, input_num_capsule]
        x = nd.transpose(x, axes=(0,2,1))
        x = nd.batch_dot(x, self.W.data())
        x = nd.expand_dims(nd.expand_dims(x, 2), 2)
        inputs_hat = nd.tile(x, [1, 1, self.num_capsule, 1, 1])

        for _ in range(self.num_routing):
            c = nd.softmax(self.bias.data())

            c_expand = nd.expand_dims(nd.expand_dims(nd.expand_dims(c, 2), 2), 0)
            # print(c_expand.shape)
            outputs = nd.sum(c_expand * inputs_hat, [1, 3], keepdims=True)
            # print('outputs',c_expand.shape)
            outputs = self.squash(outputs)
        
            self.bias.set_data(self.bias.data() + nd.sum(inputs_hat * outputs, [0, -2, -1]))
            # nd.update(self.bias, )
        outputs = nd.reshape(outputs, (self.batch_size, self.num_capsule, self.dim_vector))
        outputs = nd.transpose(outputs, axes=(0,2,1))
        return outputs


class Length(nn.Block):
    def __init__(self, **kwargs):
        super(Length, self).__init__(**kwargs)

    def forward(self, x):
        return nd.sqrt(nd.sum(nd.square(x), 1))

