// https://open.kattis.com/problems/maxflow

#include <mincostflow/graph.hpp>
#include <mincostflow/shortestpath.hpp>
#include <mincostflow/maxflow.hpp>
#include <iostream>

using value_type = int;
// typedef ln::maxflow_augmenting_path<value_type,ln::pathSearch_BFS> maxflow_t; // 1.04s
// typedef ln::maxflow_augmenting_path<value_type,ln::pathSearch_labeling> maxflow_t; // 0.04s
// typedef ln::maxflow_scaling<value_type,ln::pathSearch_BFS> maxflow_t; // 0.42s
typedef ln::maxflow_scaling<value_type,ln::pathSearch_labeling> maxflow_t; // 0.07s
// typedef ln::maxflow_preflow<value_type> maxflow_t; // 0.53s

int main()
{
    int N,M,S,T;
    std::cin >> N >> M >> S >> T;
    
    
    
    ln::digraph<int,int> Graph;
    std::vector<value_type> capacity;
    
    for(int e=0;e<M;++e)
    {
        int a,b,c;
        std::cin>>a>>b>>c;
        auto [arc,arc2] = Graph.add_arc(a,b,e);
        
        if(capacity.size()<Graph.max_num_arcs())
            capacity.resize(Graph.max_num_arcs());
            
        capacity.at(arc) = c;
        capacity.at(arc2) = 0;
    }
    
    maxflow_t f;
    
    Graph.add_node(S);
    Graph.add_node(T);
    
    using arc_pos_t = typename ln::digraph_types::arc_pos_t;
    
    const int max_flow = f.solve(
        Graph,Graph.get_node(S),Graph.get_node(T),capacity,
        [](arc_pos_t){return true;});
    
    int M_count  =0 ;
    for(int i=0;i<M;++i)
    {
        auto e = Graph.get_arc(i);
        value_type my_f = f.flow_at(Graph,e,capacity);
        M_count += (my_f > 0 ? 1 : 0);
    }
    
    
    std::cout << N << ' ' << max_flow  << ' ' << M_count << '\n';
    
    for(int i=0;i<M;++i)
    {
        auto e = Graph.get_arc(i);
        value_type my_f = f.flow_at(Graph,e,capacity);
        if(my_f==0)
            continue;
            
        auto [a,b] = Graph.arc_ends(e);
        std::cout << Graph.get_node_id(a) << ' ' << Graph.get_node_id(b) << ' ' << my_f << '\n';
    }
    
    return 0;
}
