#include "mincostflow/graph.hpp"
#include "mincostflow/maxflow.hpp"
#include <iostream>
#include <stdexcept>

#define CHECK(cond,mesg) \
    if(!(cond)) throw std::runtime_error(mesg);

template<typename pathsolver_t>
void test_case(const std::vector<std::pair<int,int>>& arcs,
               const std::vector<int> & capacity,
               const int source,
               const int sink,
               const std::vector<int>& sol)
{
    ln::digraph<int,int> graph;
    pathsolver_t solver;
    
    graph.add_node(source);
    graph.add_node(sink);
    
    std::vector<int> res_cap;
    for(auto i=0UL;i<capacity.size();++i)
    {
        auto [arc,arc2] = graph.add_arc(arcs[i].first,arcs[i].second,i);
            
        if(res_cap.size()<graph.max_num_arcs())
            res_cap.resize(graph.max_num_arcs());
        
        res_cap.at(arc) = capacity[i];
        res_cap.at(arc2) = 0;
    }
    using arc_pos_t = typename ln::digraph_types::arc_pos_t;
    
    solver.solve(graph,graph.get_node(source),graph.get_node(sink),res_cap,
            [](arc_pos_t){return true;});
    
    for(auto i=0UL;i<capacity.size();++i)
    {
        int d1 = sol[i];
        int d2 = solver.flow_at(graph,graph.get_arc(i),res_cap);
        
        CHECK(d1==d2,"test max flow: wrong flow on arc");
    }
}

template<typename pathsolver_t>
void test()
{
    { // case 1
        int source=0;
        int sink = 1;
        std::vector<int> flow{1,0,0,0,0,0};
        
        std::vector< std::pair<int,int> > arc{{0,1},{0,2},{1,3},{1,2},{1,0},{3,1}};
        std::vector<int> capacity{1,9,5,1,7,4};
        
        test_case<pathsolver_t>(arc,capacity,source,sink,flow);
    }
    { // case 2
        int source=0;
        int sink = 1;
        std::vector<int> flow{1,2,0,1,2};
        
        std::vector< std::pair<int,int> > arc{{0,2},{0,3}, {3,2},{2,1},{3,1}};
        std::vector<int> capacity{1,2,2,2,2};
        
        test_case<pathsolver_t>(arc,capacity,source,sink,flow);
    }
}

int main()
{
    using value_type = int;

    try
    {
        test< ln::maxflow_augmenting_path<value_type,ln::pathSearch_BFS>  >();
        test< ln::maxflow_augmenting_path<value_type,ln::pathSearch_labeling>  >();
        test< ln::maxflow_preflow<value_type>  >();
        test< ln::maxflow_scaling<value_type,ln::pathSearch_BFS> >();
        test< ln::maxflow_scaling<value_type,ln::pathSearch_labeling> >();
    }catch(...)
    {
        return 1;
    }
    return 0;
}


