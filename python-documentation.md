# Python-API for Pickhardt Payments

## Overview

This document describes *Pickhardt payments* Python library API.

## Example

Below there is an example use case of the Python API

```
# perform a payment from node A to node B, of amt satoshis

import pickhardtpayments

gossip = get_gossip() # whatever resource that provides a list of the channels in LN
oracle = new_oracle() # a simulation of LN or a direct connection to it

session = pickhardtpayments.paymentSession()

for channel in gossip:
    session.add_channel(channel)

res_amt = amt
while res_amt>0:
    mpp = session.optimizedPayment(A,B,res_amt)
    
    for path,value in mpp:
        success,bad_channel = oracle.send_onion(path,value)
        
        if success:
            res_amt -= value
            session.updateSuccess(path,value)
        else:
            session.updateFailure(path,value,bad_channel)
```
