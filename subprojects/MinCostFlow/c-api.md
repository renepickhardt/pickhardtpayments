Graph representation
===
The problem graph is represented by the type `lngraph`.
This data structure assumes that the graph is directed and there can be multiple edges connecting
the same pair of vertices.

The graph API is edge centered. Edges can be added, modified or removed.
Edges are refered to by their unique id, which is 64bit number that the API assigns internally.
This assignment is unspecified.

There is no need now to define an API to do the same thing for nodes, they are just added
automatically and possibly never removed from the graph. 

The constant values `lngraph_SUCCESS` and `lngraph_FAIL` are generally used as return values to
indicate the success or failure in a function call.

Memory allocation
---
Memory is allocated in the heap for a `lngraph` by calling
```
lngraph* lngraph_new();
```
This function returns a pointer to a newly created `lngraph` in a valid state.
The returned value is `NULL` if the allocation or the initialization fails.

Memory is freed by calling
```
int lngraph_free(lngraph* g);
```
No fail. You may assume this always return `lngraph_SUCCESS`.

Getters
---
Returns the number of edges.
```
int lngraph_numEdges(lngraph* g);
```
No fail.


Gets the list of edges sorted by their ids and their capacity and cost properties.
`edgeID`, `capacity` and `cost` need to be allocated to hold at least as many elements as edges in
the graph.
```
int lngraph_edges(lngraph* g, int64_t * edgeID, int64_t *capacity, int64_t * cost);
```
No fail. You may assume this always return `lngraph_SUCCESS`.


Setters
---
Edges are added to the graph by calling the function
```
int64_t lngraph_addEdge(lngraph* g, const char* nodeA_id, const char* nodeB_id, int64_t capacity,
int64_t cost);
```
The function returns a `int64_t` that corresponds to a unique identifier for the edge in the
database.
Nodes are added automatically if needed everytime `lngraph_addEdge` is called.
Possible errors: fails to add a new edge, the return value in that case is `lngraph_NOID`.
There will never be an edge whose id corresponds to `lngraph_NOID`.

Edges can be removed by calling
```
int lngraph_rmEdge(lngraph* g, int64_t edgeUniqueID);
```
No fail. You may assume this always return `lngraph_SUCCESS`.


Min. Cost Flow solver
===

Node excess. A possitive value of the excess makes a node into a *source node*
and a negative value makes it a *sink node*.
```
int lngraph_setExcess(lngraph* g, const char* nodeID, int64_t excess);
```
If the node does not exist then it will be added automatically.
Possible errors: a new node is failed to be added, in that case the returned value is `lngraph_FAIL`.
Otherwise `lngraph_SUCCESS` is returned.


Sets the excess of every known node to 0.
```
int lngraph_resetExcess(lngraph* g);
```
No fail. You may assume this always return `lngraph_SUCCESS`.

Solve the MCF problem with the excess previously set and returns the status.
```
int lngraph_mincostflow(lngraph * g,int64_t * flow);
```
The `flow` pointer points to a an allocated array of at least M elements, where M is the current
number of edges. Edges are ordered internally according to their ids and the `flow` value
corresponds to edges in that order. 
Possible errors: it was not possible to find a feasible flow that satisfy the problem constraints,
the return value is `lngraph_FAIL`. 
Otherwise `lngraph_SUCCESS` is returned.

Solve the MCF problem where there is only a source and a sink node.
This is equivalent to setting the excess of the `source` to the value `excess`
and the excess of the `sink` to `-excess` and then calling `lngraph_mincostflow`.
```
int lngraph_mincostflow_singleSinkSource(lngraph * g, 
                                         const char* source, 
                                         const char* sink,
                                         int64_t excess,
                                         int64_t * flow);
```
