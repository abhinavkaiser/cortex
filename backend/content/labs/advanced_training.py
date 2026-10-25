"""Reproducible logistic regression. Python standard library only.

Run: python3 advanced_training.py --epochs 100 --rate .1 --regularization .01
Change one factor on validation; keep test out of selection. Synthetic data
teach the protocol, not real-world fraud or medical performance.
"""
import argparse
import hashlib
import json
import math
import random


def dataset(seed=4826):
    rng=random.Random(seed)
    rows=[]
    for _ in range(96):
        features=[rng.uniform(-2,2),rng.uniform(-2,2)]
        label=int(1.4*features[0]-.8*features[1]+rng.gauss(0,.3)>.2)
        rows.append((features,label))
    return rows


def train(rate=.1, epochs=100, regularization=.01, seed=4826):
    rows=dataset(seed)
    fit,validation,test=rows[:56],rows[56:76],rows[76:]
    mean=[sum(x[j] for x,_ in fit)/len(fit) for j in range(2)]
    scale=[math.sqrt(sum((x[j]-mean[j])**2 for x,_ in fit)/len(fit)) or 1 for j in range(2)]
    weights=[0.,0.];bias=0.
    def standard(x):return [(x[j]-mean[j])/scale[j] for j in range(2)]
    def probability(x):
        z=max(-40,min(40,sum(w*v for w,v in zip(weights,standard(x)))+bias))
        return 1/(1+math.exp(-z))
    losses=[]
    for epoch in range(epochs):
        dw=[0.,0.];db=0.
        for x,y in fit:
            p=probability(x);error=p-y;norm=standard(x)
            for j in range(2):dw[j]+=error*norm[j]
            db+=error
        for j in range(2):weights[j]-=rate*(dw[j]/len(fit)+regularization*weights[j])
        bias-=rate*db/len(fit)
        if epoch in (0,epochs-1):
            loss=-sum(y*math.log(max(probability(x),1e-12))+(1-y)*math.log(max(1-probability(x),1e-12)) for x,y in fit)/len(fit)
            losses.append(dict(epoch=epoch+1,loss=round(loss,6)))
    def accuracy(partition):return sum((probability(x)>=.5)==bool(y) for x,y in partition)/len(partition)
    counts=dict(tp=0,fp=0,fn=0,tn=0)
    for x,y in test:
        predicted=probability(x)>=.5
        counts[('tp' if y else 'fp') if predicted else ('fn' if y else 'tn')]+=1
    return dict(train_count=len(fit),validation_count=len(validation),test_count=len(test),
                validation_accuracy=accuracy(validation),test_accuracy=accuracy(test),
                majority_test_accuracy=max(sum(y for _,y in test),sum(1-y for _,y in test))/len(test),
                weights=[round(w,5) for w in weights],bias=round(bias,5),seed=seed,
                dataset_sha256=hashlib.sha256(json.dumps(rows).encode()).hexdigest(),
                normalization=dict(mean=mean,scale=scale,fit_partition='train'),test_confusion=counts,losses=losses)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--epochs',type=int,default=100)
    parser.add_argument('--rate',type=float,default=.1)
    parser.add_argument('--regularization',type=float,default=.01)
    parser.add_argument('--seed',type=int,default=4826)
    args=parser.parse_args()
    if not 1<=args.epochs<=10000 or not 0<args.rate<=1 or not 0<=args.regularization<=1:
        parser.error('Use epochs 1..10000, rate (0,1], regularization [0,1].')
    print(json.dumps(train(args.rate,args.epochs,args.regularization,args.seed),indent=2))
