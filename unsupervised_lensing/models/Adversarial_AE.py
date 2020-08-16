import torch
import numpy as np
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
from torch.autograd import Variable
from torch import autograd
from tqdm import tqdm
from google_drive_downloader import GoogleDriveDownloader as gdd

class Encoder(nn.Module):

    def __init__(self,no_channels=1):
        super().__init__()

        self.conv1 = nn.Conv2d(no_channels, 16, 7, stride=3, padding=1)
        self.conv2 = nn.Conv2d(16, 32, 7, stride=3, padding=1)
        self.conv3 = nn.Conv2d(32, 64, 7)
        self.flat = nn.Flatten()
        self.linear = nn.Linear(5184, 1000)

    def forward(self, x):
        
        convolution1 = F.relu(self.conv1(x))
        convolution2 = F.relu(self.conv2(convolution1))
        convolution3 = F.relu(self.conv3(convolution2))
        Flattened = self.flat(convolution3)
        z = self.linear(Flattened)

        return z
        
class Decoder(nn.Module):

    def __init__(self,no_channels=1):
        super().__init__()

        self.linear = nn.Linear(1000, 5184)
        self.conv4 = nn.ConvTranspose2d(64, 32, 7)
        self.conv5 = nn.ConvTranspose2d(32, 16, 7, stride=3, padding=1, output_padding=2)
        self.conv6 = nn.ConvTranspose2d(16, no_channels, 6, stride=3, padding=1, output_padding=2)

    def forward(self, x):

        hidden = self.linear(x)
        Reshaped = hidden.reshape(-1,64,9,9)
        convolution4 = F.relu(self.conv4(Reshaped))
        convolution5 = F.relu(self.conv5(convolution4))
        predicted = torch.tanh(self.conv6(convolution5))

        return predicted

class Discriminator(nn.Module):

    def __init__(self, dim_z=1000 , dim_h=256):
        super(Discriminator,self).__init__()
        self.dim_z = dim_z
        self.dim_h = dim_h
        self.network = []
        self.network.extend([
            nn.Linear(self.dim_z, self.dim_h),
            nn.ReLU(),
            nn.Linear(self.dim_h, self.dim_h),
            nn.ReLU(),
            nn.Linear(self.dim_h,1),
            nn.Sigmoid(),
        ])
        self.network = nn.Sequential(*self.network)

    def forward(self, z):
        disc = self.network(z)
        return disc

def train(data_path='./Data/no_sub_train.npy',
          epochs=50,
          learning_rate=2e-3,
          beta=0,
          optimizer='Adam',
          checkpoint_path='./Weights',
          pretrain=True,
          pretrain_mode='transfer',
          pretrain_model='A'):
          
        x_train = np.load(data_path)
        x_train = x_train.astype(np.float32)
        print('Data Imported')
        
        c = x_train.shape[2]
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        encoder = Encoder(no_channels=c)
        decoder = Decoder(no_channels=c)
        Disc = Discriminator().to(device)

        if pretrain == True:
        
            if pretrain_mode == 'transfer':
            
                print('Downloading Pretrained Model Weights')
                if pretrain_model == 'A':
                    gdd.download_file_from_google_drive(file_id='1QvH1_N05bhWshv51uNvuv2mQ4tm2XjEd', dest_path=checkpoint_path + '/AAE_Dec.pth')
                    gdd.download_file_from_google_drive(file_id='1hP5X3_F0K4_5blYczmTBJvolLLBYs1hK', dest_path=checkpoint_path + '/AAE_Disc.pth')
                    gdd.download_file_from_google_drive(file_id='1KEMuQD2bWN-W7iqgKSn9ZRqkLNsc71UK', dest_path=checkpoint_path + '/AAE_Enc.pth')
                else:
                    gdd.download_file_from_google_drive(file_id='1DehaZs0F4OzAg18JG1UxGQSY6nokqfMV', dest_path=checkpoint_path + '/AAE_Dec.pth')
                    gdd.download_file_from_google_drive(file_id='1v6ZA1xfVLBqQYi1lMd4uTp2Xdj4sHqkW', dest_path=checkpoint_path + '/AAE_Disc.pth')
                    gdd.download_file_from_google_drive(file_id='1ZYCsXpGpAvqz5CZ51veyCXb5KnzaBJ1f', dest_path=checkpoint_path + '/AAE_Enc.pth')
                    
                if torch.cuda.is_available():
                    encoder = torch.load(checkpoint_path + '/AAE_Enc.pth', map_location=torch.device('cuda'))
                    decoder = torch.load(checkpoint_path + '/AAE_Dec.pth', map_location=torch.device('cuda'))
                    Disc = torch.load(checkpoint_path + '/AAE_Disc.pth', map_location=torch.device('cuda'))
                else:
                    encoder = torch.load(checkpoint_path + '/AAE_Enc.pth', map_location=torch.device('cpu'))
                    decoder = torch.load(checkpoint_path + '/AAE_Dec.pth', map_location=torch.device('cpu'))
                    Disc = torch.load(checkpoint_path + '/AAE_Disc.pth', map_location=torch.device('cpu'))
                
            if pretrain_mode == 'continue':
            
                print('Importing Pretrained Model Weights')
                if torch.cuda.is_available():
                    encoder = torch.load(checkpoint_path + '/AAE_Enc.pth', map_location=torch.device('cuda'))
                    decoder = torch.load(checkpoint_path + '/AAE_Dec.pth', map_location=torch.device('cuda'))
                    Disc = torch.load(checkpoint_path + '/AAE_Disc.pth', map_location=torch.device('cuda'))
                else:
                    encoder = torch.load(checkpoint_path + '/AAE_Enc.pth', map_location=torch.device('cpu'))
                    decoder = torch.load(checkpoint_path + '/AAE_Dec.pth', map_location=torch.device('cpu'))
                    Disc = torch.load(checkpoint_path + '/AAE_Disc.pth', map_location=torch.device('cpu'))

        ae_criterion = nn.MSELoss()
        
        if optimizer.lower() == 'adam':
            optim_encoder = torch.optim.Adam(encoder.parameters(), lr=0.001)
            optim_decoder = torch.optim.Adam(decoder.parameters(), lr=0.001)
            optim_D = torch.optim.Adam(Disc.parameters(), lr=0.001)
            optim_encoder_reg = torch.optim.Adam(encoder.parameters(), lr=0.0001)
        elif optimizer.lower() == 'rmsprop':
            optim_encoder = torch.optim.RMSprop(encoder.parameters(), lr=0.001)
            optim_decoder = torch.optim.RMSprop(decoder.parameters(), lr=0.001)
            optim_D = torch.optim.RMSprop(Disc.parameters(), lr=0.001)
            optim_encoder_reg = torch.optim.RMSprop(encoder.parameters(), lr=0.0001)
        else:
            optim_encoder = torch.optim.SGD(encoder.parameters(), lr=0.001)
            optim_decoder = torch.optim.SGD(decoder.parameters(), lr=0.001)
            optim_D = torch.optim.SGD(Disc.parameters(), lr=0.001)
            optim_encoder_reg = torch.optim.SGD(encoder.parameters(), lr=0.0001)
        
        EPS = 1e-15
        n_epochs = epochs
        print('Training the model!')
        loss_array = []
        for epoch in tqdm(range(1, n_epochs+1)):
            total_rec_loss = 0
            total_disc_loss = 0
            total_gen_loss = 0

            for i in range(x_train.shape[0]):
            
                data = torch.from_numpy(x_train[i])
                if torch.cuda.is_available():
                  data = data.cuda()

                encoding = encoder(data)
                fake = decoder(encoding)
                ae_loss = ae_criterion(fake, data)
                total_rec_loss += ae_loss.item()*data.size(0)
                
                optim_encoder.zero_grad()
                optim_decoder.zero_grad()
                ae_loss.backward()
                optim_encoder.step()
                optim_decoder.step()

                z_real_gauss = autograd.Variable(torch.randn(100, 1000) * 5.).to(device)
                D_real_gauss = Disc(z_real_gauss)

                z_fake_gauss = encoder(data)
                D_fake_gauss = Disc(z_fake_gauss)

                D_loss = -torch.mean(torch.log(D_real_gauss + EPS) + torch.log(1 - D_fake_gauss + EPS))
                total_disc_loss += D_loss.item()*data.size(0)

                optim_D.zero_grad()
                D_loss.backward()
                optim_D.step()

                z_fake_gauss = encoder(data)
                D_fake_gauss = Disc(z_fake_gauss)

                G_loss = -torch.mean(torch.log(D_fake_gauss + EPS))
                total_gen_loss += G_loss.item()*data.size(0)

                optim_encoder_reg.zero_grad()
                G_loss.backward()
                optim_encoder_reg.step()

            train_loss = total_rec_loss/x_train.shape[0]
            loss_array.append(train_loss)

            torch.save(encoder, checkpoint_path + '/AAE_Enc.pth')
            torch.save(decoder, checkpoint_path + '/AAE_Dec.pth')
            torch.save(Disc, checkpoint_path + '/AAE_Disc.pth')

        return loss_array
        
def evaluate(data_path='./Data/no_sub_test.npy',
          checkpoint_path='./Weights',
          out_path='./Results',
          pretrain=True,
          pretrain_mode='transfer',
          pretrain_model='A'):
          
        x_train = np.load(data_path)
        train_data = x_train.astype(np.float32)
        print('Data Imported')
        
        c = x_train.shape[2]
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        encoder = Encoder(no_channels=c)
        decoder = Decoder(no_channels=c)
        Disc = Discriminator().to(device)

        if pretrain == True:

            if pretrain_mode == 'transfer':
            
                print('Downloading Pretrained Model Weights')
                if pretrain_model == 'A':
                    gdd.download_file_from_google_drive(file_id='1QvH1_N05bhWshv51uNvuv2mQ4tm2XjEd', dest_path=checkpoint_path + '/AAE_Dec.pth')
                    gdd.download_file_from_google_drive(file_id='1hP5X3_F0K4_5blYczmTBJvolLLBYs1hK', dest_path=checkpoint_path + '/AAE_Disc.pth')
                    gdd.download_file_from_google_drive(file_id='1KEMuQD2bWN-W7iqgKSn9ZRqkLNsc71UK', dest_path=checkpoint_path + '/AAE_Enc.pth')
                else:
                    gdd.download_file_from_google_drive(file_id='1DehaZs0F4OzAg18JG1UxGQSY6nokqfMV', dest_path=checkpoint_path + '/AAE_Dec.pth')
                    gdd.download_file_from_google_drive(file_id='1v6ZA1xfVLBqQYi1lMd4uTp2Xdj4sHqkW', dest_path=checkpoint_path + '/AAE_Disc.pth')
                    gdd.download_file_from_google_drive(file_id='1ZYCsXpGpAvqz5CZ51veyCXb5KnzaBJ1f', dest_path=checkpoint_path + '/AAE_Enc.pth')
                    
                if torch.cuda.is_available():
                    encoder = torch.load(checkpoint_path + '/AAE_Enc.pth', map_location=torch.device('cuda'))
                    decoder = torch.load(checkpoint_path + '/AAE_Dec.pth', map_location=torch.device('cuda'))
                    Disc = torch.load(checkpoint_path + '/AAE_Disc.pth', map_location=torch.device('cuda'))
                else:
                    encoder = torch.load(checkpoint_path + '/AAE_Enc.pth', map_location=torch.device('cpu'))
                    decoder = torch.load(checkpoint_path + '/AAE_Dec.pth', map_location=torch.device('cpu'))
                    Disc = torch.load(checkpoint_path + '/AAE_Disc.pth', map_location=torch.device('cpu'))
                
            if pretrain_mode == 'continue':
            
                print('Importing Pretrained Model Weights')
                if torch.cuda.is_available():
                    encoder = torch.load(checkpoint_path + '/AAE_Enc.pth', map_location=torch.device('cuda'))
                    decoder = torch.load(checkpoint_path + '/AAE_Dec.pth', map_location=torch.device('cuda'))
                    Disc = torch.load(checkpoint_path + '/AAE_Disc.pth', map_location=torch.device('cuda'))
                else:
                    encoder = torch.load(checkpoint_path + '/AAE_Enc.pth', map_location=torch.device('cpu'))
                    decoder = torch.load(checkpoint_path + '/AAE_Dec.pth', map_location=torch.device('cpu'))
                    Disc = torch.load(checkpoint_path + '/AAE_Disc.pth', map_location=torch.device('cpu'))
                    
        else:
        
            print('Importing Pretrained Model Weights')
            if torch.cuda.is_available():
                encoder = torch.load(checkpoint_path + '/AAE_Enc.pth', map_location=torch.device('cuda'))
                decoder = torch.load(checkpoint_path + '/AAE_Dec.pth', map_location=torch.device('cuda'))
                Disc = torch.load(checkpoint_path + '/AAE_Disc.pth', map_location=torch.device('cuda'))
            else:
                encoder = torch.load(checkpoint_path + '/AAE_Enc.pth', map_location=torch.device('cpu'))
                decoder = torch.load(checkpoint_path + '/AAE_Dec.pth', map_location=torch.device('cpu'))
                Disc = torch.load(checkpoint_path + '/AAE_Disc.pth', map_location=torch.device('cpu'))

        criteria = nn.MSELoss()
        out = []
        for i in tqdm(range(train_data.shape[0])):
          data = torch.from_numpy(train_data[i])
          if torch.cuda.is_available():
            data = data.cuda()
          feature = encoder(data)
          recon = decoder(feature)
          out.append(recon.cpu().detach().numpy())
        out = np.asarray(out)

        output = []
        for i in range(out.shape[0]):
          for j in range(out[i].shape[0]):
            output.append(out[i][j])

        output = np.asarray(output)
        np.save(out_path + '/Recon_samples.npy',output)
        
        temp1 = []
        for i in range(train_data.shape[0]):
          for j in range(train_data[i].shape[0]):
            temp1.append(train_data[i][j])
        train_data = np.asarray(temp1)
        
        losses = []
        for i in range(train_data.shape[0]):
            losses.append(criteria(torch.from_numpy(train_data[i]), torch.from_numpy(output[i])))
        
        return np.asarray(losses)
