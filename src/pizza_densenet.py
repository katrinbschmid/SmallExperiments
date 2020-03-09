"""
Based on 
https://github.com/udacity/deep-learning-v2-pytorch/blob/master/intro-to-pytorch/Part%208%20-%20Transfer%20Learning%20(Solution).ipynb
"""

import time
import os
from collections import OrderedDict
 
import numpy as np
import matplotlib.pyplot as plt

import torch
from torch import nn,optim
import torch.nn.functional as F
import torchvision

#some global parameters
g_data_dir = r"../data/pizza"
g_fp = r'pizzac_0055_100_d03.pth'
ilr = 0.0055
g_dropout = 0.55
g_epochs = 50
g_changeEvery = int(g_epochs/4.5)

# TODO: Define transforms for the training data and testing data
#https://pytorch.org/docs/stable/torchvision/transforms.html
train_transforms = torchvision.transforms.Compose([
        torchvision.transforms.Resize(256),
        torchvision.transforms.RandomRotation(25),
        torchvision.transforms.RandomResizedCrop(224, scale=(0.95, 1.0)),
        torchvision.transforms.RandomHorizontalFlip(),
        torchvision.transforms.ToTensor(),
        torchvision.transforms.Normalize([0.485, 0.456, 0.406],
                                                            [0.229, 0.224, 0.225])])

test_transforms = torchvision.transforms.Compose([
        #torchvision.transforms.Resize(255),
        torchvision.transforms.CenterCrop(224),
        torchvision. transforms.ToTensor(),
        torchvision.transforms.Normalize([0.485, 0.456, 0.406],
                                                           [0.229, 0.224, 0.225])])

# Pass transforms in here, then run the next cell to see how the transforms look
train_data = torchvision.datasets.ImageFolder(g_data_dir + '/train', transform=train_transforms)
test_data = torchvision.datasets.ImageFolder(g_data_dir + '/test', transform=test_transforms)
val_data = torchvision.datasets.ImageFolder(g_data_dir + '/validation', transform=train_transforms)

batchs = 48
trainloader = torch.utils.data.DataLoader(train_data, batch_size=batchs, shuffle=True)
testloader = torch.utils.data.DataLoader(test_data, batch_size=batchs)
valloader = torch.utils.data.DataLoader(val_data, batch_size=batchs, shuffle=False)
class_names = train_data.classes

def getModel(lr=0.003):
    """
    Args:
        param1 (int): The first parameter.
        param2 (str): The second parameter.

    Returns:
        bool: The return value. True for success, False otherwise.
    """
    model = torchvision.models.densenet121(pretrained=True)
    #We can load in a model such as DenseNet. Let's print out the model architecture so we can see what's going on.
    # Freeze parameters so we don't backprop through them
    for param in model.parameters():
        param.requires_grad = False
        #param.requires_grad = True################
    
    classifier = nn.Sequential(OrderedDict([
                              ('fc1', nn.Linear(1024, 500)), # 32 x 32= 1024 flatten the input image
                              ('relu', nn.ReLU()),
                              ('fc2', nn.Linear(500, 2)),
                              ('output', nn.LogSoftmax(dim=1),
                             ) ]))
        
    model.classifier = classifier
    criterion = nn.CrossEntropyLoss()
    #nn.L1Loss()#L1 regularization 
    #criterion = torch.nn.MSELoss()#L2 regularization
    #bn_1d = nn.BatchNorm1d(num_features)
    train_loss = 0
    for device in ['cpu', 'cuda']:
        """
        torch.nn.NLLLoss(weight=None, size_average=None, ignore_index=-100, reduce=None, reduction='mean')
        The negative log likelihood loss. It is useful to train a classification problem with C classes
        """
        # Only train the classifier parameters, feature parameters are frozen
        optimizer = optim.Adam(model.classifier.parameters(), lr=0.001)
        res = model.to(device)
        for ii, (inputs, labels) in enumerate(trainloader):
            # Move input and label tensors to the GPU
            inputs, labels = inputs.to(device), labels.to(device)
            start = time.time()
            #labels tensor([1, 0, 2,
            #print(inputs, "p inputs, labels", labels)
            outputs = model.forward(inputs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            if ii==3:
                break

        print(f"p Device = {device}; Time per batch: {(time.time() - start)/3:.3f} seconds")

    # Use GPU if it's available
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = torchvision.models.densenet121(pretrained=True)
    
    # Freeze parameters so we don't backprop through them
    for param in model.parameters():
        param.requires_grad = False
        
    model.classifier = nn.Sequential(nn.Linear(1024, 256),
                                     nn.ReLU(),
                                     nn.Dropout(g_dropout),
                                     nn.Linear(256, 2),
                                     nn.LogSoftmax(dim=1)
                                     )
    criterion = nn.NLLLoss()
    # Only train the classifier parameters, feature parameters are frozen
    optimizer = optim.Adam(model.classifier.parameters(), lr=lr)
    """
        optimizer = optim.Adam([
                {'params': net.layer.weight},
                {'params': net.layer.bias, 'lr': 0.01}
            ], lr=0.1, weight_decay=0.0001)
    """
    model.to(device)
    return model, device, optimizer, criterion

def viz_layer(layer, n_filters= 4):
    fig = plt.figure(figsize=(20, 20))
    
    for i in range(n_filters):
        ax = fig.add_subplot(1, n_filters, i+1, xticks=[], yticks=[])
        # grab layer outputs
        #print(i, layer[i][0].data.cpu())
        ax.imshow(np.squeeze(layer[i][0].data.cpu().numpy()), cmap='gray')
        ax.set_title('Output %s' % str(i+1))
    plt.show()
    return

def train(model, trainloader, device, optimizer, criterion,
          g_epochs=1, print_every=10, show_layers=False, changeEvery=g_changeEvery):
    running_loss = 0
    steps = 0
    for epoch in range(g_epochs):
        # decrease learning rate
        lr = adjust_learning_rate(optimizer, epoch, every=changeEvery)
        # for data, target in train_loader:
        for inputs, labels in trainloader:
            steps += 1
            # Move input and label tensors to the default device
            inputs, labels = inputs.to(device), labels.to(device)
            optimizer.zero_grad()
            logps = model.forward(inputs)
            #Define a Loss function and optimizer
            loss = criterion(logps, labels)
            loss.backward()
            optimizer.step()
            running_loss += loss.item()
            if steps % print_every == 0:
                test_loss = 0
                accuracy = 0
                model.eval()
                with torch.no_grad():
                    for inputs, labels in testloader:
                        inputs, labels = inputs.to(device), labels.to(device)
                        #layer = [module for module in model.modules() if type(module) != nn.Sequential]
                        if show_layers:
                            viz_layer(inputs, n_filters=8)
                        logps = model.forward(inputs)
                        batch_loss = criterion(logps, labels)
                        test_loss += batch_loss.item()
                        
                        # Calculate accuracy
                        ps = torch.exp(logps)
                        top_p, top_class = ps.topk(1, dim=1)
                        equals = top_class == labels.view(*top_class.shape)
                        accuracy += torch.mean(equals.type(torch.FloatTensor)).item()
                        
                print(f"Epoch {epoch+1}/{g_epochs}.. " + str(steps)+ " lr: "+str(lr)+
                      f" Train loss: {running_loss/print_every:.3f}.. "
                      f"Test loss: {test_loss/len(testloader):.3f}.. "
                      f"Test accuracy: {accuracy/len(testloader):.3f}")
                running_loss = 0

                model.train()
                """
                   losses = []
                    for epoch in range(num_epochs):
                        running_loss = 0.0
                        for data in dataLoader:
                            images, labels = data
                            
                            outputs = model(images)
                            loss = criterion_label(outputs, labels)
                            optimizer.zero_grad()
                            loss.backward()
                            optimizer.step()
                
                            running_loss += loss.item() * images.size(0) 
                
                        epoch_loss = running_loss / len(dataloaders['train'])
                        losses.append(epoch_loss
            plt.plot(loss_values)
                """
    return

def imshow(inp, title=None):
    """Imshow for Tensor."""
    inp = inp.numpy().transpose((1, 2, 0))
    mean = np.array([0.485, 0.456, 0.406])
    std = np.array([0.229, 0.224, 0.225])
    inp = std * inp + mean
    inp = np.clip(inp, 0, 1)
    plt.imshow(inp)
    if title is not None:
        plt.title(title)
    plt.pause(0.001)  # pause a bit so that plots are updated# Get a batch of training data
    return


#https://raw.githubusercontent.com/pytorch/examples/master/mnist/main.py
def test(args, model, device, test_loader):
    model.eval()
    test_loss = 0
    correct = 0
    with torch.no_grad():
        for data, target in test_loader:
            data, target = data.to(device), target.to(device)
            output = model(data)
            test_loss += F.nll_loss(output, target, reduction='sum').item()  # sum up batch loss
            pred = output.argmax(dim=1, keepdim=True)  # get the index of the max log-probability
            correct += pred.eq(target.view_as(pred)).sum().item()
            #print( data, target, target.view_as(pred))

    test_loss /= len(test_loader.dataset)

    print('\nTest set: Average loss: {:.4f}, Accuracy: {}/{} ({:.0f}%)\n'.format(
        test_loss, correct, len(test_loader.dataset),
        100. * correct / len(test_loader.dataset)))
    return
    
def visualize_model(model, dataloader, device, num_images=6, startIndex=0, batch=0):
    """
    visualize how our model is doing on validation set.
    The above code will show you 6 (by default) images from validation set and show what our model think they are. The predictions should look quite correct at this point.
    """
    was_training = model.training
    model.eval()
    images_so_far = 2
    fig = plt.figure()   
    with torch.no_grad():
        for i, (inputs, labels) in enumerate(dataloader):
            inputs = inputs.to(device)
            labels = labels.to(device)
            outputs = model(inputs)
            _, preds = torch.max(outputs, 1)
            for j in range(startIndex, inputs.size()[0]):
                images_so_far += 1
                print(i,j, images_so_far, inputs.size()[0],"images_so_far", dataloader.dataset.samples[j][1] )
                #2D grid
                ax = plt.subplot(num_images//2, 2, images_so_far)
                ax.axis('off')
                fn = os.path.basename(dataloader.dataset.samples[j][0])
                ax.set_title('predicted: {} ({})'.format(class_names[preds[j]],fn))
                imshow(inputs.cpu().data[j])                
                if images_so_far == num_images:
                    model.train(mode=was_training)
                    return
            plt.ioff()
            plt.show()
        model.train(mode=was_training)
    return 

#TODO plot loss https://github.com/pytorch/examples/blob/master/imagenet/main.py#L327

class AverageMeter(object):
    """Computes and stores the average and current value"""
    def __init__(self, name="", fmt=':f'):
        self.name = name
        self.fmt = fmt
        self.reset()

    def reset(self):
        self.val = 0
        self.avg = 0
        self.sum = 0
        self.count = 0

    def update(self, val, n=1):
        self.val = val
        self.sum += val * n
        self.count += n
        self.avg = self.sum / self.count

    def __str__(self):
        fmtstr = '{name} {val' + self.fmt + '} ({avg' + self.fmt + '})'
        return fmtstr.format(**self.__dict__)

#https://github.com/pytorch/examples/blob/master/imagenet/main.py#L199
def adjust_learning_rate(optimizer, epoch, every=30, minimum=0.0006):
    """Sets the learning rate to the initial LR decayed by 10 % every 30 g_epochs"""
    lr = ilr  - ilr * (0.1 * (epoch // every))
    if lr < minimum:
        return minimum
    for param_group in optimizer.param_groups:
        param_group['lr'] = lr
        print(epoch, " is : ", param_group['lr'], lr, (0.1 * (epoch // every)))
    return lr
        
class ProgressMeter(object):
    def __init__(self, num_batches, meters, prefix=""):
        self.batch_fmtstr = self._get_batch_fmtstr(num_batches)
        self.meters = meters
        self.prefix = prefix

    def display(self, batch):
        entries = [self.prefix + self.batch_fmtstr.format(batch)]
        entries += [str(meter) for meter in self.meters]
        print('\t'.join(entries))

    def _get_batch_fmtstr(self, num_batches):
        num_digits = len(str(num_batches // 1))
        fmt = '{:' + str(num_digits) + 'd}'
        return '[' + fmt + '/' + fmt.format(num_batches) + ']'

def accuracy(output, target, topk=(1,)):
    """Computes the accuracy over the k top predictions for the specified values of k
    """
    with torch.no_grad():
        maxk = max(topk)
        batch_size = target.size(0)

        _, pred = output.topk(maxk, 1, True, True)
        pred = pred.t()
        correct = pred.eq(target.view(1, -1).expand_as(pred))

        res = []
        for k in topk:
            correct_k = correct[:k].view(-1).float().sum(0, keepdim=True)
            res.append(correct_k.mul_(100.0 / batch_size))
        return res


def validate(val_loader, model, criterion, device):
    """
    Args:
        param1 (int): The first parameter.
        param2 (str): The second parameter.

    Returns:
        bool: The return value. True for success, False otherwise.
    """
    args = Object
    args.gpu = device
    batch_time = AverageMeter('Time', ':6.3f')
    losses = AverageMeter('Loss', ':.4e')
    top1 = AverageMeter('Acc@1', ':6.2f')
    top5 = AverageMeter('Acc@5', ':6.2f')
    progress = ProgressMeter(
        len(val_loader),
        [batch_time, losses, top1, top5],
        prefix='Test: ')

    # switch to evaluate mode
    model.eval()
    with torch.no_grad():
        end = time.time()
        # batch
        for i, (images, target) in enumerate(val_loader):
            if args.gpu is not None:
                images = images.cuda(args.gpu, non_blocking=True)
            target = target.cuda(args.gpu, non_blocking=True)

            # compute output
            output = model(images)
            loss = criterion(output, target)

            # measure accuracy and record loss
            acc1, acc5 = accuracy(output, target, topk=(1, 5))
            losses.update(loss.item(), images.size(0))
            top1.update(acc1[0], images.size(0))
            top5.update(acc5[0], images.size(0))

            # measure elapsed time
            batch_time.update(time.time() - end)
            end = time.time()

            if i % args.print_freq == 0:
                progress.display(i)

        # TODO: this should also be done with the ProgressMeter
        print(' * Acc@1 {top1.avg:.3f} Acc@5 {top5.avg:.3f}'
              .format(top1=top1, top5=top5))
    return top1.avg


def save_checkpoint(state, is_best, filename='checkpoint.pth.tar'):
    """
    Args:
        param1 (int): The first parameter.
        param2 (str): The second parameter.

    Returns:
        bool: The return value. True for success, False otherwise.
    """
    torch.save(state, filename)
    if is_best:
        shutil.copyfile(filename, 'model_best.pth.tar')
    return


def main():
    model, device, optimizer, criterion = getModel(lr=ilr)
    inputs, classes = next(iter(trainloader))# Make a grid from batch
    sample_train_images = torchvision.utils.make_grid(inputs)
    #helper.imshow(sample_train_images, title=classes)
    if os.path.isfile(g_fp):
        state_dict = torch.load(g_fp)
        #print(state_dict.keys())
        model.load_state_dict(state_dict)
    else:
        train(model, trainloader, device, optimizer, criterion,
               g_epochs=g_epochs, print_every=8)
        torch.save(model.state_dict(), g_fp)
    test(None, model, device, valloader)
    #validate(valloader, model, criterion, device)
    #visualize_model(model, valloader, device, 6, 12, 0)
    visualize_model(model, valloader, device, 6, 47, 0)

    plt.ioff()
    plt.show()
    return 0

print(class_names)
main()
print("done")

