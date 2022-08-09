#include "mincostflow/graph.hpp"
#include "mincostflow/maxflow.hpp"
#include "mincostflow/mincostflow.hpp"
#include <iostream>
#include <stdexcept>

#define CHECK(cond,mesg) \
    if(!(cond)) throw std::runtime_error(mesg);

template<typename pathsolver_t>
void test_case(const std::vector<std::pair<int,int>>& arcs,
               const std::vector<int> & capacity,
               const std::vector<int> & weight,
               const int source,
               const int sink,
               const std::vector<int>& sol)
{
    ln::digraph<int,int> graph;
    pathsolver_t solver;
    
    graph.add_node(source);
    graph.add_node(sink);
    
    std::vector<int> res_cap;
    std::vector<int> res_cost;
    for(auto i=0UL;i<capacity.size();++i)
    {
        auto [arc,arc2] = graph.add_arc(arcs[i].first,arcs[i].second,i);
            
        res_cap.resize(graph.max_num_arcs());
        res_cost.resize(graph.max_num_arcs());
        
        res_cap.at(arc) = capacity[i];
        res_cap.at(arc2) = 0;
        
        res_cost.at(arc) = weight[i];
        res_cost.at(arc2) = -weight[i];
    }
    // using arc_pos_t = typename ln::digraph_types::arc_pos_t;
    
    solver.solve(graph,graph.get_node(source),graph.get_node(sink),res_cost,res_cap);
    
    // std::cerr << "Flow: ";
    for(auto i=0UL;i<capacity.size();++i)
    {
        int d1 = sol[i];
        int d2 = solver.flow_at(graph,graph.get_arc(i),res_cap);
        // std::cerr << " " << d2;
        
        CHECK(d1==d2,"test max flow: wrong flow on arc");
    }
    // std::cerr << '\n';
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
        std::vector<int> weight{1,1,1,1,1,1};
        
        test_case<pathsolver_t>(arc,capacity,weight,source,sink,flow);
    }
    { // case 2
        int source=0;
        int sink = 1;
        std::vector<int> flow{1,2,0,1,2};
        
        std::vector< std::pair<int,int> > arc{{0,2},{0,3}, {3,2},{2,1},{3,1}};
        std::vector<int> capacity{1,2,2,2,2};
        std::vector<int> weight{1,1,1,1,1,1};
        
        test_case<pathsolver_t>(arc,capacity,weight,source,sink,flow);
    }
    {
        // case 3
        int source=0;
        int sink=1;
        std::vector<int> flow{2,5,2,0,0};
        std::vector< std::pair<int,int> > arc{{0,2},{0,1},{2,1},{1,3},{0,3}};
        std::vector<int> capacity{2,5,7,8,6};
        std::vector<int> weight{1,3,2,2,6};
        
        test_case<pathsolver_t>(arc,capacity,weight,source,sink,flow);
    }
    {
        // case 4
        int source = 0;
        int sink = 1;
        std::vector<int> flow{0,4,1,0,0,1,1,0};
        std::vector< std::pair<int,int> > arc{{0,2},{0,1},{0,3},{1,3},{2,3},{2,1},{3,2},{3,0}};
        std::vector<int> capacity{2,4,3,3,3,1,1,4};
        std::vector<int> weight{2,3,1,0,2,0,0,4};
        
        test_case<pathsolver_t>(arc,capacity,weight,source,sink,flow);
    }
    {
        // case 5
        int source = 0;
        int sink = 1;
        std::vector<int> flow{1,1,0,0,1,2};
        std::vector< std::pair<int,int> > arc{{0,3},{0,2},{1,2},{1,0},{2,3},{3,1}};
        std::vector<int> capacity{2,1,1,1,4,2};
        std::vector<int> weight{4,1,0,1,2,0};
        
        test_case<pathsolver_t>(arc,capacity,weight,source,sink,flow);
        
    }
}

int main()
{
    using value_type = int;

    try
    {
        test< ln::mincostflow_EdmondsKarp<
                                           value_type,
                                           ln::shortestPath_FIFO<value_type> > >();
        test< ln::mincostflow_EdmondsKarp<
                                           value_type,
                                           ln::shortestPath_BellmanFord<value_type> > >();
                                           
        // expected failure
        // test< ln::mincostflow_EdmondsKarp<
        //                                    value_type,
        //                                    ln::shortestPath_Dijkstra<value_type> > >();
    
    
        test< ln::mincostflow_PrimalDual<
                                          ln::shortestPath_FIFO<value_type>,
                                          ln::maxflow_augmenting_path<value_type,ln::pathSearch_BFS> >>();
        test< ln::mincostflow_PrimalDual<
                                          ln::shortestPath_FIFO<value_type>,
                                          ln::maxflow_augmenting_path<value_type,ln::pathSearch_labeling> >>();
        test< ln::mincostflow_PrimalDual<
                                          ln::shortestPath_FIFO<value_type>,
                                          ln::maxflow_scaling<value_type,ln::pathSearch_BFS> >>();
        test< ln::mincostflow_PrimalDual<
                                          ln::shortestPath_FIFO<value_type>,
                                          ln::maxflow_scaling<value_type,ln::pathSearch_labeling> >>();
        test< ln::mincostflow_PrimalDual<
                                          ln::shortestPath_FIFO<value_type>,
                                          ln::maxflow_preflow<value_type> >>();
                                          
                                          
        test< ln::mincostflow_PrimalDual<
                                          ln::shortestPath_BellmanFord<value_type>,
                                          ln::maxflow_augmenting_path<value_type,ln::pathSearch_BFS> >>();
        test< ln::mincostflow_PrimalDual<
                                          ln::shortestPath_BellmanFord<value_type>,
                                          ln::maxflow_augmenting_path<value_type,ln::pathSearch_labeling> >>();
        test< ln::mincostflow_PrimalDual<
                                          ln::shortestPath_BellmanFord<value_type>,
                                          ln::maxflow_scaling<value_type,ln::pathSearch_BFS> >>();
        test< ln::mincostflow_PrimalDual<
                                          ln::shortestPath_BellmanFord<value_type>,
                                          ln::maxflow_scaling<value_type,ln::pathSearch_labeling> >>();
        test< ln::mincostflow_PrimalDual<
                                          ln::shortestPath_BellmanFord<value_type>,
                                          ln::maxflow_preflow<value_type> >>();
                                          
                                          
        test< ln::mincostflow_PrimalDual<
                                          ln::shortestPath_Dijkstra<value_type>,
                                          ln::maxflow_augmenting_path<value_type,ln::pathSearch_BFS> >>();
        test< ln::mincostflow_PrimalDual<
                                          ln::shortestPath_Dijkstra<value_type>,
                                          ln::maxflow_augmenting_path<value_type,ln::pathSearch_labeling> >>();
        test< ln::mincostflow_PrimalDual<
                                          ln::shortestPath_Dijkstra<value_type>,
                                          ln::maxflow_scaling<value_type,ln::pathSearch_BFS> >>();
        test< ln::mincostflow_PrimalDual<
                                          ln::shortestPath_Dijkstra<value_type>,
                                          ln::maxflow_scaling<value_type,ln::pathSearch_labeling> >>();
        test< ln::mincostflow_PrimalDual<
                                          ln::shortestPath_Dijkstra<value_type>,
                                          ln::maxflow_preflow<value_type> >>();
        
        
        
        
        
        test< ln::mincostflow_capacityScaling< 
                                          ln::shortestPath_FIFO<value_type>,
                                          ln::maxflow_augmenting_path<value_type,ln::pathSearch_BFS> 
                                               >> ();
        test< ln::mincostflow_capacityScaling< 
                                          ln::shortestPath_FIFO<value_type>,
                                          ln::maxflow_augmenting_path<value_type,ln::pathSearch_labeling> 
                                               >> ();
        test< ln::mincostflow_capacityScaling< 
                                          ln::shortestPath_FIFO<value_type>,
                                          ln::maxflow_scaling<value_type,ln::pathSearch_BFS> 
                                               >> ();
        test< ln::mincostflow_capacityScaling< 
                                          ln::shortestPath_FIFO<value_type>,
                                          ln::maxflow_scaling<value_type,ln::pathSearch_labeling> 
                                               >> ();
        test< ln::mincostflow_capacityScaling< 
                                          ln::shortestPath_FIFO<value_type>,
                                          ln::maxflow_preflow<value_type> 
                                               >> ();
        test< ln::mincostflow_capacityScaling< 
                                          ln::shortestPath_BellmanFord<value_type>,
                                          ln::maxflow_augmenting_path<value_type,ln::pathSearch_BFS> 
                                               >> ();
        test< ln::mincostflow_capacityScaling< 
                                          ln::shortestPath_BellmanFord<value_type>,
                                          ln::maxflow_augmenting_path<value_type,ln::pathSearch_labeling> 
                                               >> ();
        test< ln::mincostflow_capacityScaling< 
                                          ln::shortestPath_BellmanFord<value_type>,
                                          ln::maxflow_scaling<value_type,ln::pathSearch_BFS> 
                                               >> ();
        test< ln::mincostflow_capacityScaling< 
                                          ln::shortestPath_BellmanFord<value_type>,
                                          ln::maxflow_scaling<value_type,ln::pathSearch_labeling> 
                                               >> ();
        test< ln::mincostflow_capacityScaling< 
                                          ln::shortestPath_BellmanFord<value_type>,
                                          ln::maxflow_preflow<value_type> 
                                               >> ();
        
        test< ln::mincostflow_capacityScaling< 
                                          ln::shortestPath_Dijkstra<value_type>,
                                          ln::maxflow_augmenting_path<value_type,ln::pathSearch_BFS> 
                                               >> ();
        test< ln::mincostflow_capacityScaling< 
                                          ln::shortestPath_Dijkstra<value_type>,
                                          ln::maxflow_augmenting_path<value_type,ln::pathSearch_labeling> 
                                               >> ();
        test< ln::mincostflow_capacityScaling< 
                                          ln::shortestPath_Dijkstra<value_type>,
                                          ln::maxflow_scaling<value_type,ln::pathSearch_BFS> 
                                               >> ();
        test< ln::mincostflow_capacityScaling< 
                                          ln::shortestPath_Dijkstra<value_type>,
                                          ln::maxflow_scaling<value_type,ln::pathSearch_labeling> 
                                               >> ();
        test< ln::mincostflow_capacityScaling< 
                                          ln::shortestPath_Dijkstra<value_type>,
                                          ln::maxflow_preflow<value_type> 
                                               >> ();
        
        test< ln::mincostflow_costScaling< 
                                          ln::maxflow_augmenting_path<value_type,ln::pathSearch_BFS> 
                                                >> ();
        test< ln::mincostflow_costScaling< 
                                          ln::maxflow_augmenting_path<value_type,ln::pathSearch_labeling> 
                                               >> ();
        test< ln::mincostflow_costScaling< 
                                          ln::maxflow_scaling<value_type,ln::pathSearch_BFS> 
                                               >> ();
        test< ln::mincostflow_costScaling< 
                                          ln::maxflow_scaling<value_type,ln::pathSearch_labeling> 
                                               >> ();
        test< ln::mincostflow_costScaling< 
                                          ln::maxflow_preflow<value_type> 
                                               >> ();
    }catch(std::exception& e)
    {
        std::cerr << e.what() << '\n';
        return 1;
    }
    return 0;
}


