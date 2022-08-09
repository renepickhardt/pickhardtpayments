// https://open.kattis.com/problems/shortestpath1

#include "mincostflow/graph.hpp"
#include "mincostflow/shortestpath.hpp"
#include <iostream>

using length_type = int;
typedef ln::shortestPath_Dijkstra<length_type> pathsolver_t; // 0.28s
//typedef ln::shortestPath_FIFO<length_type> pathsolver_t; // 1.14s
//typedef ln::shortestPath_BellmanFord<length_type> pathsolver_t; // >3.0s

int main()
{

    while(1)
    {
        int N_vertex,N_edges,Q,S;
        std::cin>>N_vertex>>N_edges>>Q>>S;
        if(N_vertex==0)break;
        
        ln::digraph<int,int> Graph;
        std::vector<length_type> weights(N_edges);
        pathsolver_t solver;
        
        
        for(int e=0;e<N_edges;++e)
        {
            int a,b,w;
            std::cin>> a>>b>>w;
            auto [arc,arc2] = Graph.add_arc(a,b,e);
            
            if(weights.size()<Graph.max_num_arcs())
                weights.resize(Graph.max_num_arcs());
                
            weights.at(arc) = w;
            weights.at(arc2) = solver.INFINITY;
        }
        
        using arc_pos_t = typename ln::digraph_types::arc_pos_t;
        // using node_pos_t = typename ln::digraph_types::node_pos_t;
        
        auto s_node = Graph.add_node(S);
        solver.solve(Graph,s_node,weights,
            [&weights,&solver](arc_pos_t arc){return weights.at(arc)<solver.INFINITY;});
        
        
        for(int v;Q--;)
        {
            std::cin>>v; 
            auto pos = Graph.get_node(v);
            if(Graph.is_valid(pos) && solver.distance.at(pos)<solver.INFINITY)
            {
                std::cout << solver.distance.at(pos.x) << '\n';
            }
            else
            {
                std::cout << "Impossible\n";
            }
        }
        
        std::cout<<'\n';
    }
    return 0;
}
