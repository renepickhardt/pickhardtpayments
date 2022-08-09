#include <mincostflow/mincostflow.hpp>
#include <iostream>
#include <chrono>
#include <ortools/graph/min_cost_flow.h>
#include <ortools/graph/max_flow.h>

typedef long long value_type;
typedef int nodeID_type;
typedef int arcID_type;
typedef ln::digraph<nodeID_type,arcID_type> graph_type;

// typedef ln::maxflow_augmenting_path<value_type,ln::pathSearch_BFS> maxflow_t;
// typedef ln::maxflow_augmenting_path<value_type,ln::pathSearch_labeling> maxflow_t;
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

// typedef ln::mincostflow_capacityScaling<
//    ln::shortestPath_Dijkstra<value_type>,maxflow_t> mincostflow_t;
// TLE

struct integer_graph
{
    graph_type g;
    std::vector<value_type> capacity;
    std::vector<value_type> weight;
    
    integer_graph(int N_nodes)
    {
        for(nodeID_type i=0;i<N_nodes;++i)
            g.add_node(i);
    }
    auto size()const
    {
        return g.num_nodes();
    }
    void add_arc(nodeID_type a,nodeID_type b, arcID_type e)
    {
        g.add_arc(a,b,e);
    }
    void set_capacity(const std::vector<value_type>& cap)
    {
        capacity.resize(g.max_num_arcs());
        for(arcID_type i=0;i<cap.size();++i)
        {
            auto arc = g.get_arc(i);
            auto dual = g.arc_dual(arc);
            
            capacity[arc] = cap[i];
            capacity[dual]=0;
        }
    }
    void set_cost(const std::vector<value_type>& cost)
    {
        weight.resize(g.max_num_arcs());
        for(arcID_type i=0;i<cost.size();++i)
        {
            auto arc = g.get_arc(i);
            auto dual = g.arc_dual(arc);
            
            weight[arc] = cost[i];
            weight[dual]= -cost[i];
        }
    }
    
    auto capacity_at(arcID_type e)const
    {
        auto arc = g.get_arc(e);
        auto dual = g.arc_dual(arc);
        return capacity[arc]+capacity[dual];
    }
    auto capacity_at(graph_type::arc_pos_t arc)const
    {
        auto dual = g.arc_dual(arc);
        return capacity[arc]+capacity[dual];
    }
    auto cost_at(arcID_type e)const
    {
        auto arc = g.get_arc(e);
        return weight[arc];
    }
    auto cost_at(graph_type::arc_pos_t arc)const
    {
        return weight[arc];
    }
    auto flow_at(arcID_type e)const
    {
        auto arc = g.get_arc(e);
        auto dual = g.arc_dual(arc);
        return capacity[dual];
    }
    auto flow_at(graph_type::arc_pos_t arc)const
    {
        auto dual = g.arc_dual(arc);
        return capacity[dual];
    }
};

std::pair<value_type,value_type> solve_ortools(
    const int N_nodes,
    nodeID_type S, nodeID_type T,
    const std::vector<std::pair<nodeID_type,nodeID_type>>& edges,
    const std::vector<value_type>& cap,
    const std::vector<value_type>& cost,
    const std::string tname)
{
    auto start = std::chrono::high_resolution_clock::now();
    operations_research::SimpleMaxFlow max_flow;
    operations_research::SimpleMinCostFlow mincost_flow;
    
    for(int i=0;i<cap.size();++i)
    {
        auto [a,b] = edges[i];
        max_flow.AddArcWithCapacity(a,b,cap[i]);
        mincost_flow.AddArcWithCapacityAndUnitCost(a,b,cap[i],cost[i]);
    }
    
    for(int i=0;i<N_nodes;++i)
    {
        mincost_flow.SetNodeSupply(i,0);
    }
    
    
    int status = max_flow.Solve(S,T);
    const value_type Flow = max_flow.OptimalFlow();
    
    mincost_flow.SetNodeSupply(S,Flow);
    mincost_flow.SetNodeSupply(T,-Flow);
    
    int min_status = mincost_flow.Solve();
    const value_type Cost = mincost_flow.OptimalCost();
   
   auto stop = std::chrono::high_resolution_clock::now();
    
    std::cout << tname << " " <<
    std::chrono::duration_cast<std::chrono::microseconds>(stop-start) .count()
    << std::endl;
    
    return {Flow,Cost};
}

    
template<typename mincostflow_t>
void solve(integer_graph& G,
           const std::vector<value_type>& capacity,
           const std::vector<value_type>& cost,
           nodeID_type S,
           nodeID_type T,
           std::string tname)
{
    G.set_capacity(capacity);
    G.set_cost(cost);
    
    auto& graph = G.g;
    
    auto start = std::chrono::high_resolution_clock::now();
    mincostflow_t f;
    f.solve(graph,graph.get_node(S),graph.get_node(T),G.weight,G.capacity);
    auto stop = std::chrono::high_resolution_clock::now();
    
    std::cout << tname << " " <<
    std::chrono::duration_cast<std::chrono::microseconds>(stop-start) .count()
    << std::endl;
}

std::pair<value_type,value_type> 
check_constraints(
           const integer_graph& G,
           const std::vector<std::pair<int,int>>& ed_list,
           const std::vector<value_type>& capacity,
           const std::vector<value_type>& cost,
           const nodeID_type S,
           const nodeID_type T,
           const int N_nodes,
           const int N_edges)
{
    // check capacity constraint
    for(int e=0;e<N_edges;++e)
    {
        const auto c = G.capacity_at(e);
        assert(capacity[e]==c);
        const auto f = G.flow_at(e);
        assert(c>=f && f>=0);
    }
    
    // check balances
    std::vector<value_type> balance(N_nodes,0);
    
    for(int e=0;e<N_edges;++e)
    {
        auto [a,b] = ed_list[e];
        auto f = G.flow_at(e);
        balance[a] -= f;
        balance[b] += f;
    }
    
    for(int i=0;i<N_nodes;++i)
    if(i!=S && i!=T)
    {
        assert(balance[i]==0);
    }
    
    const auto Flow = balance[T];
    
    assert(Flow>=0);
    assert(balance[S] == -balance[T]);
    
    value_type Cost = 0;
    for(int e=0;e<N_edges;++e)
    {
        Cost += G.flow_at(e) * G.cost_at(e);
    }
    
    // std::cout << "Max flow = " << Flow << " Min cost = " << Cost << '\n';
    return {Flow,Cost};
}

int main()
{   
    int N,M,S,T;
    std::cin >> N >> M >> S >> T;
    
    integer_graph G(N);
    std::vector<std::pair<int,int>> ed_list; 
    std::vector<value_type> capacity;
    std::vector<value_type> weight;
    
    for(int e=0;e<M;++e)
    {
        int a,b,wei,cap;
        std::cin>>a>>b>>cap>>wei;
        
        G.add_arc(a,b,e);
        
        ed_list.push_back({a,b});
        capacity.push_back(cap);
        weight.push_back(wei);
    }
    
    
    solve<
        ln::mincostflow_EdmondsKarp<
            value_type,
            ln::shortestPath_FIFO<value_type> >
        >(G,capacity,weight,S,T,"Edmonds-Karp");
    auto [flow_0,cost_0] = check_constraints(G,ed_list,capacity,weight,S,T,N,M);
    
    {
        solve<
                ln::mincostflow_PrimalDual<
                    ln::shortestPath_Dijkstra<value_type>,
                    ln::maxflow_augmenting_path<value_type,ln::pathSearch_labeling> 
                    >
                >(G,capacity,weight,S,T,"Primal-dual");
        auto [flow,cost] = check_constraints(G,ed_list,capacity,weight,S,T,N,M);
        
        assert(flow_0==flow && cost_0==cost);
    }
        
    // { 
    //     solve<
    //             ln::mincostflow_capacityScaling< 
    //                 ln::shortestPath_Dijkstra<value_type>,
    //                 ln::maxflow_augmenting_path<value_type,ln::pathSearch_labeling> 
    //                 >
    //             >(G,capacity,weight,S,T,"Capacity-scaling");
    //     auto [flow,cost] = check_constraints(G,ed_list,capacity,weight,S,T,N,M);
    //     assert(flow_0==flow && cost_0==cost);
    // }
    { 
        solve<
                ln::mincostflow_costScaling< 
                    ln::maxflow_augmenting_path<value_type,ln::pathSearch_labeling> 
                    >
                >(G,capacity,weight,S,T,"Cost-scaling");
        auto [flow,cost] = check_constraints(G,ed_list,capacity,weight,S,T,N,M);
        assert(flow_0==flow && cost_0==cost);
    }
    {
        auto [flow,cost] = solve_ortools(N,S,T,ed_list,capacity,weight,"Ortools");
        assert(flow_0==flow && cost_0==cost);
    }
    return 0;
}

