# C-API for Pickhardt Payments

## Overview

This document describes *Pickhardt payments* C library API.

## Primitive data types

Nodes ID are encoded as 33 bytes numbers.
```
typedef char[33] nodeID_t;
```

Channels ID are encoded as 8 bytes numbers.
```
typedef uint64_t channelID_t;
```

## Payment Session

A `paymentSession` is an object that contains all the information known about the Lightning Network
from the initial knowledge of the public channels and the accumulated information
resulting from successful and failed attempts to forward payments while the session is in use.
```
typedef struct paymentSession paymentSession;
```

To create and initialize a `paymentSession` the function `paymentSession_new` must be called.
This function returns a pointer to a newly allocated `paymentSession`.
This function returns `NULL` if the necessary memory couldn't be allocated.
```
paymentSession* paymentSession_new();
```

To cleanup and release the memory one needs to call `paymentSession_delete`.
This function does not fail.
```
void paymentSession_delete(paymentSession* s);
```

Internally a Session represents the Lightning-Network graph of nodes and channels.
Initially a newly created Session has no knowled of any channel nor nodes, so one has to provide
this information by means of the function `paymentSession_addChannel`.
This function returns an error code that could have the values:
`PAYMENTSESSION_SUCCESS` if no errors occurred or
`PAYMENTSESSION_BADALLOC` if this function failed to allocate the memory for the new channel.
```
int paymentSession_addChannel(paymentSession* s,
                              channelID_t short_channel_id,
                              nodeID_t Source,
                              nodeID_t Dest,
                              int64_t capacity,
                              int64_t fee_rate,
                              int64_t base_fee);
```

A channel can be removed by calling `paymentSession_rmChannel`.
This function returns an error code.
```
int paymentSession_rmChannel(paymentSession* s,
                              channelID_t short_channel_id,
                              nodeID_t Source,
                              nodeID_t Dest);
```

A Session can be used to compute a multipart-payment with maximum probability of success based on
the knowledge of the Lightning-Network topology, channels capacity and previous knowledge of the
state of the liquidity in the channels.
By calling `paymentSession_optimizedPayment` one obtains a pointer to a `multiPartPayment` object
that contains a multipart-payment canditate based on the `amount` requested to be forwarded between
nodes `Source` and `Dest`.
This function returns `NULL` if the `paymentSession_optimizedPayment` fails.
The variable `status` contains an error code to log the cause of the failure.
```
multiPartPayment* paymentSession_optimizedPayment(paymentSession* s,
                                                  nodeID_t Source,
                                                  nodeID_t Dest,
                                                  int64_t amount,
                                                  char* status);
```

Once an onion is sent to the Lightning-Network from the success or failure of this attempt we can
update our knowledge of the liquidity of the channels involved in that onion. That information can
be used by the Session to compute future payments attempts.
To update the knowledge of the Network one must call `paymentSession_updateKnowledge`.
This function returns an error code.
```
int paymentSession_updateKnowledge(paymentSession* s,
                                   int64_t short_channel_id,
                                   nodeID_t Source,
                                   nodeID_t Dest,
                                   int64_t amount,
                                   char status);
```

The accumulated knowledge in the Session can be erased by calling
`paymentSession_forgetInformation`.
This function returns an error code.
```
int paymentSession_forgetInformation(paymentSession* s);
```

## Multipart Payments

The function `paymentSession_optimizedPayment` produces a multipart payment (MPP) based on the
knowledge accumulated in the Session in use. The object that implements the concept of that MPP is
the `multiPartPayment`. We do not expose a constructor for this object in the public interface,
because it will always represent the result of an `paymentSession_optimizedPayment` and nothing
else. The `multiPartPayment` exposes an interface to query information about the MPP that the
Session has computed, therefore all of the `multiPartPayment_*` functions, except for the
destructor, do not modify the state of the MPP, the `multiPartPayment` is read-only.
```
typedef struct multiPartPayment multiPartPayment;
```

Once a `multiPartPayment` object is no longer used, it can be freed by calling
`multiPartPayment_delete`. This function never fails.
```
void multiPartPayment_delete(multiPartPayment* mpp);
```

`multiPartPayment` can be queried to get the information about the MPP information they encode.
To query the amount of satoshis this payment sends one calls `multiPartPayment_amount`.
This function never fails.
```
int64_t multiPartPayment_amount(const multiPartPayment* mpp);
```

To query the source and the destination of the payment the functions
`multiPartPayment_source` and `multiPartPayment_destination` are called respectively.
These functions never fail.
```
nodeID_t multiPartPayment_source(const multiPartPayment* mpp);
```
```
nodeID_t multiPartPayment_destination(const multiPartPayment* mpp);
```

Each MPP consist of a list of paths in the channels/nodes graph.
By calling `multiPartPayment_numParts` one can query for the number of paths that constitute the
MPP.
This functions never fails.
```
uint64_t multiPartPayment_numParts(const multiPartPayment* mpp);
```

By calling `multiPartPayment_pathLengths` one can query the length of the individual paths that make
the MPP. The pointer `lengths` must be previously allocated to hold at least as many paths as the
MPP.
This function never fails.
```
void multiPartPayment_pathLengths(const multiPartPayment* mpp,
                                  uint64_t* lengths);
```

Similar to the `multiPartPayment_pathLengths`, the function `multiPartPayment_pathValues` queries
the MPP to obtain the amount of satoshis commited to each individual path.
The pointer `values` must be previously allocated to hold at least as many paths as the
MPP.
This function never fails.
```
void multiPartPayment_pathValues(const multiPartPayment* mpp,
                                 int64_t* values);
```

The function `multiPartPayment_pathChannels` writes the list of channels for every path in the MPP
to the input array `short_channel_id`, and for each of these channels a value of the `orientation`
is set either to `CHANNEL_FORWARD` or `CHANNEL_BACKWARD` to indicate the direction the liquidity is
transfered. If the satoshis are transfered from a node with lowest lexicographical order to the
other then the `orientation` is set to `CHANNEL_FORWARD`, otherwise it is `CHANNEL_BACKWARD`.
This function never fails.
```
void multiPartPayment_pathChannels(const multiPartPayment* mpp,
                                   int64_t* short_channel_id,
                                   char* orientation);
```

## Example

```
// TODO
```
