// https://open.kattis.com/problems/mincostmaxflow
#include <mincostflow/mincostflow.hpp>
#include <iostream>

typedef long long value_type;

// typedef ln::maxflow_augmenting_path<value_type,ln::pathSearch_BFS> maxflow_t;
typedef ln::maxflow_augmenting_path<value_type,ln::pathSearch_labeling> maxflow_t;
// typedef ln::maxflow_scaling<value_type,ln::pathSearch_BFS> maxflow_t;
// typedef ln::maxflow_scaling<value_type,ln::pathSearch_labeling> maxflow_t;
// typedef ln::maxflow_preflow<value_type> maxflow_t;

//typedef ln::mincostflow_EdmondsKarp<
//    value_type,ln::shortestPath_FIFO<value_type>> mincostflow_t; // 2.18s
// typedef ln::mincostflow_EdmondsKarp<
//     value_type,ln::shortestPath_BellmanFord<value_type>> mincostflow_t; // TLE
// typedef ln::mincostflow_EdmondsKarp<ln::shortestPath_Dijkstra> mincostflow_t; // expected failure

// typedef ln::mincostflow_PrimalDual<
//    ln::shortestPath_FIFO<value_type>,maxflow_t> mincostflow_t; // 2.54s, 3.02s, 2.75s, 3.18s, TLE
// typedef ln::mincostflow_PrimalDual<
//    ln::shortestPath_BellmanFord<value_type>,maxflow_t> mincostflow_t; // TLE
//typedef ln::mincostflow_PrimalDual<
//    ln::shortestPath_Dijkstra<value_type>,maxflow_t> mincostflow_t;
// 1.34s, 1.76s, 1.52s, 2.42s, TLE

//typedef ln::mincostflow_capacityScaling<
//    ln::shortestPath_Dijkstra<value_type>,maxflow_t> mincostflow_t;
// TLE
typedef ln::mincostflow_costScaling<
    maxflow_t> mincostflow_t; //0.37s, 0.06s, 0.10s, 0.07s, 0.15s

int main()
{
    int N,M,S,T;
    std::cin >> N >> M >> S >> T;
    
    ln::digraph<int,int> G;
    std::vector<value_type> capacity;
    std::vector<value_type> weight;
    
    G.add_node(S);
    G.add_node(T);
    
    for(int e=0;e<M;++e)
    {
        int a,b,c,w;
        std::cin>>a>>b>>c>>w;
        auto [arc,arc2] = G.add_arc(a,b,e);
        
        capacity.resize(G.max_num_arcs());
        weight.resize(G.max_num_arcs());
        
        capacity[arc] = c;
        capacity[arc2]=0;
        
        weight[arc] = w;
        weight[arc2]=-w;
    }
    
    mincostflow_t f;
    
    auto Flow = f.solve(G,G.get_node(S),G.get_node(T),weight,capacity);
    long long Cost = 0;
    
    for(int e=0;e<M;++e)
    {
        auto arc = G.get_arc(e);
        Cost+= static_cast<long long>(weight[arc])*f.flow_at(G,arc,capacity);
    }
    
    std::cout << Flow << " " << Cost << '\n';
    
    return 0;
}

