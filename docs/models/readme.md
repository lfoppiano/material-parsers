## Notes on models and evaluation 


### base

```
max_epoch: 60
early_stop: True
patience: 5
batch_size (training): 20
max_sequence_length: 3000
model_name: grobid-material-parsers-base-BidLSTM_CRF
learning_rate:  0.001
use_ELMo:  False
```

```
                  precision    recall  f1-score   support

        <doping>     0.6976    0.6528    0.6745       265
   <fabrication>     0.4545    0.1136    0.1818        44
       <formula>     0.8326    0.8443    0.8384      2569
          <name>     0.7850    0.8040    0.7944       949
         <shape>     0.8990    0.9631    0.9300       841
     <substrate>     0.6341    0.5270    0.5756       148
         <value>     0.8565    0.8769    0.8666       463
      <variable>     0.9544    0.9821    0.9681       448

all (micro avg.)     0.8359    0.8458    0.8408      5727
```

### base + incremental (same data)

learning_rate:  0.0001

```
                  precision    recall  f1-score   support

        <doping>     0.7309    0.6151    0.6680       265
   <fabrication>     0.4706    0.1818    0.2623        44
       <formula>     0.8242    0.8431    0.8336      2569
          <name>     0.7671    0.8019    0.7841       949
         <shape>     0.9061    0.9643    0.9343       841
     <substrate>     0.5895    0.3784    0.4609       148
         <value>     0.8608    0.8683    0.8645       463
      <variable>     0.9604    0.9754    0.9679       448

all (micro avg.)     0.8323    0.8388    0.8356      5727

```

### base + incremental (same data) + incremental (additional data)

learning_rate:  0.0001

```
                  precision    recall  f1-score   support

        <doping>     0.6835    0.6113    0.6454       265
   <fabrication>     0.4286    0.2045    0.2769        44
       <formula>     0.8412    0.8435    0.8424      2569
          <name>     0.7606    0.8103    0.7847       949
         <shape>     0.9013    0.9667    0.9329       841
     <substrate>     0.5714    0.3243    0.4138       148
         <value>     0.8596    0.8726    0.8660       463
      <variable>     0.9608    0.9844    0.9724       448

all (micro avg.)     0.8356    0.8404    0.8380      5727
```

### base 2 

```
max_epoch: 60
early_stop: True
patience: 5
batch_size (training): 20
max_sequence_length: 3000
model_name: grobid-material-parsers-base-BidLSTM_CRF
learning_rate:  0.001
use_ELMo:  False
```

```
                  precision    recall  f1-score   support

        <doping>     0.7639    0.6717    0.7149       265
   <fabrication>     0.3333    0.0682    0.1132        44
       <formula>     0.8303    0.8459    0.8380      2569
          <name>     0.7461    0.7987    0.7715       949
         <shape>     0.9078    0.9596    0.9329       841
     <substrate>     0.5952    0.3378    0.4310       148
         <value>     0.8685    0.8985    0.8832       463
      <variable>     0.9503    0.9821    0.9660       448

all (micro avg.)     0.8333    0.8425    0.8379      5727

```
### base2 + incremental (same data) + incremental (additional data)

learning_rate:  0.0001

```
                  precision    recall  f1-score   support

        <doping>     0.7208    0.6528    0.6851       265
   <fabrication>     0.3529    0.1364    0.1967        44
       <formula>     0.8478    0.8497    0.8488      2569
          <name>     0.7681    0.8166    0.7916       949
         <shape>     0.9117    0.9703    0.9401       841
     <substrate>     0.6000    0.3243    0.4211       148
         <value>     0.8539    0.8834    0.8684       463
      <variable>     0.9587    0.9844    0.9714       448

all (micro avg.)     0.8429    0.8470    0.8450      5727
```