#include "mincostflow/graph.hpp"
#include "mincostflow/shortestpath.hpp"
#include <iostream>
#include <stdexcept>

#define CHECK(cond,mesg) \
    if(!(cond)) throw std::runtime_error(mesg);

template<typename pathsolver_t>
void test_case(const std::vector<std::pair<int,int>>& arcs,
               const std::vector<int> & length,
               const int source,
               const std::vector<int>& sol)
{
    ln::digraph<int,int> graph;
    pathsolver_t solver;
    
    for(auto i=0UL;i<sol.size();++i)
    {
        graph.add_node(i);
    }
    
    std::vector<int> weights;
    for(auto i=0UL;i<length.size();++i)
    {
        auto [arc,arc2] = graph.add_arc(arcs[i].first,arcs[i].second,i);
            
        if(weights.size()<graph.max_num_arcs())
            weights.resize(graph.max_num_arcs());
        
        weights.at(arc) = length[i];
        weights.at(arc2) = solver.INFINITY;
    }
    using arc_pos_t = typename ln::digraph_types::arc_pos_t;
    
    solver.solve(graph,graph.get_node(source),weights,
            [&weights,&solver](arc_pos_t arc){return weights.at(arc)<solver.INFINITY;});
    
    for(auto i=0UL;i<sol.size();++i)
    {
        int d1 = sol[i];
        int d2 = solver.distance.at(graph.get_node(i));
        
        CHECK(d1==d2,"test shortest path: found different distances");
    }
}

template<typename pathsolver_t>
void test()
{
    { // case 1
        int source=0;
        std::vector<int> distance{0,1,2,6};
        
        std::vector< std::pair<int,int> > arc{{0,1},{0,2},{1,3},{1,2},{1,0},{3,1}};
        std::vector<int> length{1,9,5,1,7,4};
        
        test_case<pathsolver_t>(arc,length,source,distance);
    }
    { // case 2
        int source=0;
        std::vector<int> distance{0,4,11,9};
        
        std::vector< std::pair<int,int> > arc{{0,1},{1,3},{1,0},{1,2},{2,1},{3,2}};
        std::vector<int> length{4,5,4,7,7,3};
        
        test_case<pathsolver_t>(arc,length,source,distance);
    }
}

int main()
{
    using length_type = int;

    try
    {
        test< ln::shortestPath_Dijkstra<length_type>  >();
        test< ln::shortestPath_FIFO<length_type>  >();
        test< ln::shortestPath_BellmanFord<length_type>  >();
    }catch(...)
    {
        return 1;
    }
    return 0;
}

