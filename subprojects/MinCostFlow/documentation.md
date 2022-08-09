Graph representation
===
```
    class digraph;
```

Path solvers
===

Finds a path in a directed graph with un-weighted edges.
```
    class pathSearch_BFS;
```

Finds a path in a directed graph with un-weighted edges.
This label-relabel search algorithm has meaninful state.
Figure 7.6 of Ahuja 93.
```
    class pathSearch_labeling;
```

Pseudo-polynomial generic path optimization.
```
    class shortestPath_FIFO;
```
    
Bellman-Ford path optimization
```
    class shortestPath_BellmanFord;
```

Dijkstra path optimization.
```
    class shortestPath_Dijkstra;
```

Max-flow
===

Generic augmenting path algorithm, template on the path finder algorithm.
Ahuja figure 6.12.
```
    template<typename path_solver_type>
    class maxflow_augmenting_path;
```

Capacity scaling algorithm template on the path finder.
Ahuja figure 7.3.
```
    template<typename path_solver_type>
    class maxflow_scaling;
```

Preflow-push algorithm.
Ahuja figure 7.12.
```
    class maxflow_preflow;
```

Min-Cost-Flow
===
Min-cost-max-flow based on Edmonds-Karp augmenting path algorithm, it greedily
searches for the smallest cost routes. The path optimizer could be any shortest
path algorithm that deals with negative weights.
```
    template<typename path_optimizer_type>
    class mincostflow_EdmondsKarp;
```

Min-cost-max-flow Primal Dual algorithm.
It uses a potential function to set the edges costs to zero and it pushes flow
along cost-zero edges.
It is a template on a path optimizer and a maxflow engines.
The path optimizer could be any shortest path algorithm including Dijkstra.
```
    template<typename path_optimizer_type, typename maxflow_type>
    class mincostflow_PrimalDual;
```
